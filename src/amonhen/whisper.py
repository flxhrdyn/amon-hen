"""Whisper ONNX speech recognition and timestamped transcription engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from amonhen.store import SpeechSegment

if TYPE_CHECKING:
    import onnxruntime as ort
    from tokenizers import Tokenizer


# Special token constants for Whisper
SOT_TOKEN = 50258  # <|startoftranscript|>
EN_TOKEN = 50259  # <|en|>
TRANSCRIBE_TOKEN = 50359  # <|transcribe|>
NO_TIMESTAMPS_TOKEN = 50363  # <|notimestamps|>
EOT_TOKEN = 50257  # <|endoftranscript|>
FIRST_TIMESTAMP_TOKEN = 50364  # <|0.00|>


def compute_mel_filterbank(sr: int = 16000, n_fft: int = 400, n_mels: int = 80) -> np.ndarray:
    """Compute Slaney-style triangular Mel filterbank matrix."""
    f_min = 0.0
    f_max = float(sr // 2)

    m_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
    m_max = 2595.0 * np.log10(1.0 + f_max / 700.0)
    m_pts = np.linspace(m_min, m_max, n_mels + 2)
    f_pts = 700.0 * (10.0 ** (m_pts / 2595.0) - 1.0)

    bins = np.floor((n_fft + 1) * f_pts / sr).astype(int)
    fb = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)

    for m in range(1, n_mels + 1):
        f_m_minus = bins[m - 1]
        f_m = bins[m]
        f_m_plus = bins[m + 1]

        if f_m > f_m_minus:
            fb[m - 1, f_m_minus:f_m] = (np.arange(f_m_minus, f_m) - f_m_minus) / (f_m - f_m_minus)
        if f_m_plus > f_m:
            fb[m - 1, f_m:f_m_plus] = (f_m_plus - np.arange(f_m, f_m_plus)) / (f_m_plus - f_m)

    return fb


def compute_log_mel_spectrogram(
    audio: np.ndarray,
    n_mels: int = 80,
    n_fft: int = 400,
    hop_length: int = 160,
) -> np.ndarray:
    """Compute 80-channel log-Mel spectrogram padded to 3000 frames (30 seconds)."""
    if len(audio) == 0:
        return np.zeros((1, n_mels, 3000), dtype=np.float32)

    target_samples = 30 * 16000
    if len(audio) < target_samples:
        audio = np.pad(audio, (0, target_samples - len(audio)))
    else:
        audio = audio[:target_samples]

    window = np.hanning(n_fft).astype(np.float32)
    num_frames = 1 + (len(audio) - n_fft) // hop_length

    # Create sliding window views over audio
    shape = (num_frames, n_fft)
    strides = (audio.strides[0] * hop_length, audio.strides[0])
    frames = np.lib.stride_tricks.as_strided(audio, shape=shape, strides=strides)

    stft = np.fft.rfft(frames * window, n=n_fft)
    magnitudes = np.abs(stft) ** 2

    fb = compute_mel_filterbank(sr=16000, n_fft=n_fft, n_mels=n_mels)
    mel = np.dot(magnitudes, fb.T)

    log_spec = np.log10(np.maximum(mel, 1e-5))
    log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0

    spec = log_spec.T[np.newaxis, :, :3000].astype(np.float32)
    if spec.shape[2] < 3000:
        spec = np.pad(spec, ((0, 0), (0, 0), (0, 3000 - spec.shape[2])))
    return spec


class WhisperTranscriber:
    """Transcribes audio using CPU-optimized Whisper ONNX sessions."""

    def __init__(
        self,
        encoder_session: ort.InferenceSession,
        decoder_session: ort.InferenceSession,
        tokenizer: Tokenizer,
    ):
        self.encoder = encoder_session
        self.decoder = decoder_session
        self.tokenizer = tokenizer

    @classmethod
    def from_pretrained(
        cls,
        repo_id: str = "onnx-community/whisper-tiny",
    ) -> WhisperTranscriber:
        """Download and load Whisper ONNX model from Hugging Face Hub."""
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        encoder_path = hf_hub_download(repo_id=repo_id, filename="onnx/encoder_model.onnx")
        decoder_path = hf_hub_download(repo_id=repo_id, filename="onnx/decoder_model.onnx")
        tokenizer_path = hf_hub_download(repo_id=repo_id, filename="tokenizer.json")

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 4
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        encoder = ort.InferenceSession(
            encoder_path, sess_options=sess_options, providers=["CPUExecutionProvider"]
        )
        decoder = ort.InferenceSession(
            decoder_path, sess_options=sess_options, providers=["CPUExecutionProvider"]
        )
        tokenizer = Tokenizer.from_file(tokenizer_path)

        return cls(encoder, decoder, tokenizer)

    def transcribe_window(
        self,
        audio_30s: np.ndarray,
        offset_ms: int = 0,
        max_tokens: int = 128,
    ) -> list[SpeechSegment]:
        """Transcribe a 30-second audio window and return timestamped segments."""
        if len(audio_30s) == 0:
            return []

        # Check if the window is practically silent
        if np.max(np.abs(audio_30s)) < 0.005:
            return []

        mel = compute_log_mel_spectrogram(audio_30s)

        # 1. Run ONNX Encoder
        encoder_inputs = {self.encoder.get_inputs()[0].name: mel}
        encoder_outputs = self.encoder.run(None, encoder_inputs)
        hidden_states = encoder_outputs[0]

        # 2. Autoregressive Greedy Decoding
        current_tokens = [SOT_TOKEN, EN_TOKEN, TRANSCRIBE_TOKEN]
        segments: list[SpeechSegment] = []

        active_start_ms = offset_ms
        collected_text_tokens: list[int] = []

        dec_inputs = self.decoder.get_inputs()
        hidden_input_name = dec_inputs[1].name if len(dec_inputs) > 1 else "encoder_hidden_states"
        token_input_name = dec_inputs[0].name

        for _ in range(max_tokens):
            input_ids = np.array([current_tokens], dtype=np.int64)
            decoder_feed = {
                token_input_name: input_ids,
                hidden_input_name: hidden_states,
            }

            logits = self.decoder.run(None, decoder_feed)[0]
            next_token = int(np.argmax(logits[0, -1, :]))

            if next_token == EOT_TOKEN:
                break

            current_tokens.append(next_token)

            # Prevent hallucination loops during instrumental/silent sections
            if len(current_tokens) >= 8 and current_tokens[-4:] == current_tokens[-8:-4]:
                break
            if len(current_tokens) >= 5 and len(set(current_tokens[-4:])) == 1:
                break

            # Check for timestamp tokens (token >= FIRST_TIMESTAMP_TOKEN)
            # Each timestamp token step is 20ms (0.02s)
            if next_token >= FIRST_TIMESTAMP_TOKEN:
                ts_ms = offset_ms + int((next_token - FIRST_TIMESTAMP_TOKEN) * 20)
                if collected_text_tokens:
                    text = self.tokenizer.decode(collected_text_tokens).strip()
                    if text:
                        segments.append(
                            SpeechSegment(
                                start_ms=active_start_ms,
                                end_ms=max(ts_ms, active_start_ms + 500),
                                text=text,
                            )
                        )
                    collected_text_tokens = []
                active_start_ms = ts_ms
            else:
                collected_text_tokens.append(next_token)

        # Flush any trailing text tokens
        if collected_text_tokens:
            text = self.tokenizer.decode(collected_text_tokens).strip()
            if text:
                segments.append(
                    SpeechSegment(
                        start_ms=active_start_ms,
                        end_ms=offset_ms + 30000,
                        text=text,
                    )
                )

        return segments

    def transcribe(
        self,
        audio: np.ndarray,
        chunk_len_sec: int = 30,
    ) -> list[SpeechSegment]:
        """Transcribe arbitrary duration 16kHz audio array."""
        if len(audio) == 0:
            return []

        chunk_samples = chunk_len_sec * 16000
        all_segments: list[SpeechSegment] = []

        for offset in range(0, len(audio), chunk_samples):
            chunk = audio[offset : offset + chunk_samples]
            offset_ms = int((offset / 16000.0) * 1000)
            window_segments = self.transcribe_window(chunk, offset_ms=offset_ms)
            all_segments.extend(window_segments)

        return all_segments
