# AmonHen Stage 3 (Result Quality) - Design Spec

> *"From the Seat of Seeing, no moment remains hidden."*

Tanggal: 2026-08-26  
Status: Disetujui (Tahap Perancangan Selesai)

---

## 1. Ringkasan

Dokumen ini mendefinisikan desain teknis untuk **Stage 3: Kualitas Hasil (Result Quality)** pada AmonHen.
Tahap ini mengubah fungsionalitas pencarian dari pencarian frame individual mentah menjadi pencarian segmen temporal berbobot dengan kalibrasi ambang skor statistik.

Tujuan utama:
1. **Segment Merging:** Menggabungkan frame kandidat yang berdekatan secara temporal dalam satu video menjadi satu rentang waktu kejadian (`start_ms` sampai `end_ms`) dengan representative best-scoring timestamp (`best_ts_ms`).
2. **Score Calibration & Filtering:** Mengeliminasi hasil pencarian tidak relevan (*false positives*) saat kueri tidak ditemukan di dalam koleksi video, menggunakan baseline distribusi acak per video dan opsi batas manual.

---

## 2. Struktur Data

### 2.1 Model `Segment`

Model data hasil pencarian baru menggantikan representasi `Hit` tunggal untuk hasil akhir:

```python
@dataclass(frozen=True)
class Segment:
    video_id: int
    video_path: str
    start_ms: int       # Awal rentang waktu momen (ms)
    end_ms: int         # Akhir rentang waktu momen (ms)
    best_ts_ms: int     # Timestamp frame dengan skor tertinggi di dalam segmen
    score: float        # Skor kemiripan kosinus puncak (peak similarity)
    frame_count: int    # Jumlah frame yang menyusun segmen ini
```

Untuk segmen yang hanya terdiri dari 1 frame terisolasi, nilai `start_ms == end_ms == best_ts_ms` dan `frame_count == 1`.

---

## 3. Algoritma Penggabungan Segmen (*Segment Merging*)

### 3.1 Alur Pengambilan & Penggabungan

1. **Oversampling Kandidat:**
   Pencarian vektor awal di `sqlite-vec` mengambil $k_{\text{candidates}} = \max(\text{limit} \times 8, 32)$ frame kandidat lintas seluruh video terindeks.

2. **Penyaringan Skor Ambang (*Threshold Filter*):**
   Setiap frame kandidat diuji terhadap nilai ambang batas relevansi:
   * Jika `--min-score` ditentukan secara manual, gunakan nilai tersebut.
   * Jika tidak dan kalibrasi aktif, gunakan `score_baseline` milik video asal frame.
   * Frame dengan skor di bawah ambang batas langsung dibuang.

3. **Pengelompokan per Video & Pengurutan Temporal:**
   Frame kandidat yang lolos dikelompokkan berdasarkan `video_id` dan diurutkan berdasarkan `ts_ms` secara menaik (*ascending*).

4. **Merge Iteration (`max_gap_ms`):**
   Untuk setiap video, frame dirangkai:
   * Inisialisasi segmen dengan frame pertama: `start_ms = hit.ts_ms`, `end_ms = hit.ts_ms`, `best_ts_ms = hit.ts_ms`, `score = hit.score`, `frame_count = 1`.
   * Untuk frame berikutnya, jika $\Delta t = \text{hit.ts\_ms} - \text{current\_end\_ms} \le \text{max\_gap\_ms}$:
     - Perbarui `end_ms = hit.ts_ms`.
     - Jika $\text{hit.score} > \text{current\_score}$, perbarui `score = hit.score` dan `best_ts_ms = hit.ts_ms`.
     - Tambahkan `frame_count += 1`.
   * Jika $\Delta t > \text{max\_gap\_ms}$:
     - Simpan segmen saat ini, lalu mulai segmen baru.

5. **Global Sorting & Truncation:**
   Seluruh segmen gabungan dari semua video dikumpulkan, diurutkan berdasarkan `score` menurun (*descending*), dan dipotong hingga `limit` teratas.

---

## 4. Kalibrasi Skor Statistik (*Score Calibration*)

### 4.1 Penghitungan Baseline saat Pengindeksan

Ketika sebuah video selesai diindeks (`index_videos`):
1. Sistem mengambil sampel acak hingga 50 vektor embedding dari tabel `vec_frame` milik video tersebut.
2. Dihitung distribusi pairwise similarity antar sampel acak (atau terhadap embedding netral) untuk mendapatkan rata-rata $\mu$ dan simpangan baku $\sigma$.
3. Ambang batas dasar dihitung:
   $$\text{score\_baseline} = \mu + 1.5 \times \sigma$$
4. Nilai disimpan ke dalam kolom `score_baseline` pada tabel `video` di SQLite.

### 4.2 Penerapan saat Pencarian

* Jika kueri dijalankan dan semua frame memiliki skor di bawah ambang batas (baseline atau manual), sistem mengembalikan daftar kosong (`[]`), dan antarmuka mengabarkan `No results.`

---

## 5. Antarmuka CLI & Format Tampilan

### 5.1 Perintah `search`

```bash
amon-hen search "<query>" [OPTIONS]

Options:
  -k, --limit INTEGER     Maksimum jumlah segmen hasil. [default: 10]
  --merge-gap FLOAT       Jeda waktu maksimum (detik) antar frame untuk digabung. [default: 4.0]
  --min-score FLOAT       Ambang skor minimal manual (0.0 - 1.0). [default: None]
  --no-calibrate          Nonaktifkan penyaringan baseline otomatis. [default: False]
  --json                  Output data dalam format JSON murni.
  --db PATH               Path database indeks.
  --model TEXT            Model ID.
```

### 5.2 Format Teks Human-Readable

* Segmen rentang waktu:
  ```
   1. 00:01:05.0 - 00:01:08.0  0.270  cctv-people-demo.webm
  ```
* Segmen frame tunggal:
  ```
   2. 00:00:06.0              0.263  cctv-people-demo.webm
  ```
* Format kolom sejajar dan waktu berformat `HH:MM:SS.s`.

### 5.3 Format JSON

```json
{
  "query": "a person holding an umbrella",
  "results": [
    {
      "video": "cctv-people-demo.webm",
      "start_ms": 65000,
      "end_ms": 68000,
      "best_ts_ms": 66000,
      "score": 0.2702,
      "frame_count": 4
    }
  ]
}
```

---

## 6. Rencana Pengujian

1. **Unit Test Penggabungan Segmen (`tests/test_pipeline.py` / `tests/test_segment.py`):**
   * Penggabungan frame berdekatan dalam satu video.
   * Frame yang melebihi `max_gap_ms` tidak digabung.
   * Isolasi antar video (frame dengan timestamp sama di video berbeda tidak boleh digabung).
   * Pemilihan `best_ts_ms` dan `score` tertinggi dalam satu segmen.
   * Single frame menjadi segmen dengan `start_ms == end_ms`.

2. **Unit Test Kalibrasi & Filtering:**
   * Pengujian pembuangan kandidat di bawah `min_score` manual.
   * Pengujian pembuangan kandidat di bawah `score_baseline`.
   * Penonaktifan kalibrasi dengan `--no-calibrate`.

3. **Integrasi CLI:**
   * Verifikasi formatting rentang waktu di stdout.
   * Verifikasi struktur data JSON pada flag `--json`.
