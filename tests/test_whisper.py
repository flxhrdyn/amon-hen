from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from amonhen.store import SpeechSegment
from amonhen.whisper import (
    WhisperTranscriber,
    compute_log_mel_spectrogram,
)


def test_compute_log_mel_spectrogram_shape_and_range():
    # 5 seconds of 16kHz audio
    audio = np.random.uniform(-0.5, 0.5, size=16000 * 5).astype(np.float32)
    spec = compute_log_mel_spectrogram(audio)

    assert spec.shape == (1, 80, 3000)
    assert spec.dtype == np.float32
    assert not np.isnan(spec).any()
    assert not np.isinf(spec).any()


def test_whisper_transcriber_decodes_tokens_with_mock_sessions():
    mock_encoder = MagicMock()
    mock_encoder.get_inputs.return_value = [MagicMock(name="input_features")]
    mock_encoder.run.return_value = [np.zeros((1, 1500, 384), dtype=np.float32)]

    mock_decoder = MagicMock()
    mock_decoder.get_inputs.return_value = [
        MagicMock(name="input_ids"),
        MagicMock(name="encoder_hidden_states"),
    ]

    # Token 100: " hello", Token 200: " world"
    tokens = [50364, 100, 200, 50464, 50257]
    call_count = 0

    def mock_decoder_run(output_names, input_feed):
        nonlocal call_count
        logits = np.zeros((1, 1, 51865), dtype=np.float32)
        target_token = tokens[call_count] if call_count < len(tokens) else 50257
        logits[0, 0, target_token] = 30.0
        call_count += 1
        return [logits]

    mock_decoder.run.side_effect = mock_decoder_run

    mock_tokenizer = MagicMock()
    mock_tokenizer.decode.return_value = "hello world"

    transcriber = WhisperTranscriber(
        encoder_session=mock_encoder,
        decoder_session=mock_decoder,
        tokenizer=mock_tokenizer,
    )

    audio = np.random.uniform(0.1, 0.5, size=16000 * 3).astype(np.float32)
    segments = transcriber.transcribe(audio)

    assert len(segments) >= 1
    assert isinstance(segments[0], SpeechSegment)
    assert "hello world" in segments[0].text
    assert segments[0].start_ms == 0
    assert segments[0].end_ms == 2000


def test_whisper_transcribe_handles_empty_audio():
    mock_encoder = MagicMock()
    mock_decoder = MagicMock()
    mock_tokenizer = MagicMock()

    transcriber = WhisperTranscriber(
        encoder_session=mock_encoder,
        decoder_session=mock_decoder,
        tokenizer=mock_tokenizer,
    )

    segments = transcriber.transcribe(np.array([], dtype=np.float32))
    assert segments == []


def test_get_language_token_resolves_codes():
    from amonhen.whisper import get_language_token

    mock_tokenizer = MagicMock()
    mock_tokenizer.token_to_id.side_effect = lambda tok: (
        50275 if tok == "<|id|>" else (50266 if tok == "<|ja|>" else 50259)
    )

    assert get_language_token("id", mock_tokenizer) == 50275
    assert get_language_token("indonesian", mock_tokenizer) == 50275
    assert get_language_token("ja", mock_tokenizer) == 50266
    assert get_language_token("japanese", mock_tokenizer) == 50266
    assert get_language_token("en", mock_tokenizer) == 50259
    assert get_language_token("unknown_lang", mock_tokenizer) == 50259


def test_whisper_transcriber_uses_specified_language_token():
    in_feat = MagicMock()
    in_feat.name = "input_features"
    mock_encoder = MagicMock()
    mock_encoder.get_inputs.return_value = [in_feat]
    mock_encoder.run.return_value = [np.zeros((1, 1500, 384), dtype=np.float32)]

    captured_prompt = []
    in_ids = MagicMock()
    in_ids.name = "input_ids"
    in_hidden = MagicMock()
    in_hidden.name = "encoder_hidden_states"

    mock_decoder = MagicMock()
    mock_decoder.get_inputs.return_value = [in_ids, in_hidden]

    def mock_decoder_run(output_names, input_feed):
        nonlocal captured_prompt
        input_ids = input_feed.get("input_ids")
        if len(captured_prompt) == 0 and input_ids is not None:
            captured_prompt = list(input_ids[0])
        logits = np.zeros((1, 1, 51865), dtype=np.float32)
        logits[0, 0, 50257] = 30.0  # EOT immediately
        return [logits]

    mock_decoder.run.side_effect = mock_decoder_run

    mock_tokenizer = MagicMock()
    mock_tokenizer.token_to_id.side_effect = lambda tok: 50275 if tok == "<|id|>" else 50259

    transcriber = WhisperTranscriber(
        encoder_session=mock_encoder,
        decoder_session=mock_decoder,
        tokenizer=mock_tokenizer,
    )

    audio = np.random.uniform(0.1, 0.5, size=16000 * 2).astype(np.float32)
    transcriber.transcribe(audio, language="id")

    # Prefix must be [<|startoftranscript|>, <|id|> (50275), <|transcribe|>]
    assert len(captured_prompt) >= 3
    assert captured_prompt[1] == 50275


def test_whisper_transcriber_detects_language_automatically():
    in_feat = MagicMock()
    in_feat.name = "input_features"
    mock_encoder = MagicMock()
    mock_encoder.get_inputs.return_value = [in_feat]
    mock_encoder.run.return_value = [np.zeros((1, 1500, 384), dtype=np.float32)]

    captured_prompt = []
    in_ids = MagicMock()
    in_ids.name = "input_ids"
    in_hidden = MagicMock()
    in_hidden.name = "encoder_hidden_states"

    mock_decoder = MagicMock()
    mock_decoder.get_inputs.return_value = [in_ids, in_hidden]

    call_num = 0

    def mock_decoder_run(output_names, input_feed):
        nonlocal call_num, captured_prompt
        input_ids = input_feed.get("input_ids")
        logits = np.zeros((1, 1, 51865), dtype=np.float32)
        if call_num == 0:
            # Language detection step: simulate Japanese (50266) having highest logit
            logits[0, 0, 50266] = 50.0
        else:
            if len(captured_prompt) == 0 and input_ids is not None:
                captured_prompt = list(input_ids[0])
            logits[0, 0, 50257] = 30.0  # EOT immediately
        call_num += 1
        return [logits]

    mock_decoder.run.side_effect = mock_decoder_run

    mock_tokenizer = MagicMock()
    mock_tokenizer.token_to_id.return_value = 50259

    transcriber = WhisperTranscriber(
        encoder_session=mock_encoder,
        decoder_session=mock_decoder,
        tokenizer=mock_tokenizer,
    )

    audio = np.random.uniform(0.1, 0.5, size=16000 * 2).astype(np.float32)
    transcriber.transcribe(audio, language="auto")

    # Prefix must have auto-detected Japanese (50266)
    assert len(captured_prompt) >= 3
    assert captured_prompt[1] == 50266
