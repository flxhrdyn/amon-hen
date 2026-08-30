# AmonHen Stage 4 (Benchmark & Evaluation) - Design Spec

> *"From the Seat of Seeing, no moment remains hidden."*

Tanggal: 2026-08-26  
Status: Disetujui (Tahap Perancangan Selesai)

---

## 1. Ringkasan

Dokumen ini mendefinisikan desain teknis untuk **Stage 4: Benchmark & Evaluasi** pada AmonHen.
Harness benchmark ini dirancang sebagai modul evaluasi terisolasi untuk membuktikan efisiensi dan kualitas pencarian AmonHen secara kuantitatif berdasarkan metodologi standar ilmiah *Video Moment Retrieval* (VMR) / *Temporal Grounding*.

Tujuan utama:
1. **Verifikasi Kualitas Retrieval:** Mengukur **Recall@1 (IoU=0.3/0.5)**, **Recall@5 (IoU=0.3/0.5)**, dan **mIoU** terhadap subset standar publik (**Charades-STA**).
2. **Pengukuran Efisiensi Nyata:** Mengukur **Kecepatan Indexing** (rasio terhadap durasi video realtime), **Latensi Kueri** (ms/pencarian), **Rasio Pemangkasan Frame**, dan **Jejak Penyimpanan SQLite** (MB/jam video).
3. **Komparasi Empiris:** Membandingkan secara langsung antara:
   - Baseline: Fixed Sampler (1.0 fps).
   - Adaptive Sampler (Perceptual Hash + Blur Filtering).
   - Adaptive Sampler + Embedding-Similarity Dedup.

---

## 2. Struktur Modul

Harness benchmark ditempatkan di direktori terpisah [`benchmarks/`](file:///C:/Users/Felix/Documents/1_HOME/Projects/Python/compvis/amon-hen/benchmarks) agar tidak menjadi dependensi runtime pada paket distribusi PyPI:

```
benchmarks/
├── __init__.py
├── dataset.py      # Dataset loader, downloader mini-subset Charades-STA, & synthetic harness
├── metrics.py      # Rumus matematis IoU, Recall@K, mIoU, speedup, latency
└── run.py          # Runner utama CLI & generator tabel Markdown
```

---

## 3. Metodologi & Formulasi Metrik

### 3.1 Intersection over Union (IoU) Rentang Waktu
Diberikan rentang waktu prediksi $P = [t_{p,\text{start}}, t_{p,\text{end}}]$ dan rentang *ground truth* $G = [t_{g,\text{start}}, t_{g,\text{end}}]$ dalam detik:
$$\text{Intersection}(P, G) = \max\left(0, \min(t_{p,\text{end}}, t_{g,\text{end}}) - \max(t_{p,\text{start}}, t_{g,\text{start}})\right)$$
$$\text{Union}(P, G) = \max(t_{p,\text{end}}, t_{g,\text{end}}) - \min(t_{p,\text{start}}, t_{g,\text{start}})$$
$$\text{IoU}(P, G) = \frac{\text{Intersection}(P, G)}{\text{Union}(P, G)}$$

Jika $\text{Union}(P, G) \le 0$, maka $\text{IoU} = 0$.

### 3.2 Recall@K pada Ambang Batas $\theta$ ($\text{R@K, IoU}=\theta$)
Untuk sekumpulan kueri $Q$ dengan $K \in \{1, 5\}$ dan $\theta \in \{0.3, 0.5\}$:
$$\text{Recall@K}(\theta) = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \mathbb{I}\left( \max_{1 \le i \le K} \text{IoU}(P_{q,i}, G_q) \ge \theta \right)$$
di mana $P_{q,i}$ adalah segmen prediksi ke-$i$ untuk kueri $q$.

### 3.3 mean IoU (mIoU)
Rata-rata IoU dari segmen peringkat teratas ($P_1$) terhadap seluruh kueri:
$$\text{mIoU} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \text{IoU}(P_{q,1}, G_q)$$

### 3.4 Efisiensi Sistem
* **Indexing Speedup:**
  $$\text{Speedup} = \frac{\sum \text{Durasi Video (s)}}{\sum \text{Waktu Indexing (s)}}$$
* **Query Latency:** Rata-rata waktu eksekusi end-to-end (embedding teks + vector search + segment merging) dalam milidetik.
* **Storage Footprint:** Total ukuran file database SQLite per 1 jam durasi video ($\text{MB}/\text{jam}$).
* **Frames Kept Ratio:** $\frac{\text{Frames Stored}}{\text{Frames Decoded}} \times 100\%$.

---

## 4. Dataset & Anotasi Ground Truth

### 4.1 Format File Anotasi (`dataset.py`)
Dataset dikemas dalam struktur JSON standar:

```json
[
  {
    "video_path": "path/to/video.mp4",
    "duration_s": 30.0,
    "annotations": [
      {
        "query": "a person holding a cup",
        "start_s": 5.0,
        "end_s": 12.5
      }
    ]
  }
]
```

### 4.2 Synthetic Video Generator
Untuk pengujian CI/CD dan luring (offline) tanpa mengunduh video besar dari internet, `dataset.py` menyediakan generator video sintetis berbasis ffmpeg dengan durasi dan pergerakan objek/warna yang deterministik untuk memvalidasi fungsi harness.

---

## 5. Output & Runner CLI

### 5.1 Perintah Eksekusi
```bash
uv run python -m benchmarks.run [OPTIONS]

Options:
  --data-dir PATH         Direktori dataset video dan anotasi.
  --output PATH           Path untuk menyimpan tabel Markdown keluaran.
  --samples INTEGER       Jumlah video sampel yang dievaluasi.
  --synthetic             Gunakan dataset sintetis offline untuk uji cepat.
```

### 5.2 Format Keluaran Tabel Markdown
```markdown
| Sampler Configuration | R@1 (IoU=0.3) | R@1 (IoU=0.5) | R@5 (IoU=0.3) | mIoU | Indexing Speed | Latency | Storage / Jam |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fixed (1.0 fps)** | 0.xx | 0.xx | 0.xx | 0.xx | 8.2x RT | 18 ms | 12.5 MB |
| **Adaptive (Default)** | 0.xx | 0.xx | 0.xx | 0.xx | 18.5x RT | 12 ms | 4.2 MB |
| **Adaptive + Embed-Dedup** | 0.xx | 0.xx | 0.xx | 0.xx | 22.1x RT | 9 ms | 2.8 MB |
```

---

## 6. Rencana Pengujian Harness (`tests/test_benchmarks.py`)

1. **Unit Test Metrik (`tests/test_benchmark_metrics.py`):**
   * Pengujian perhitungan IoU (overlap sempurna = 1.0, disjoin = 0.0, partial overlap).
   * Pengujian Recall@1 dan Recall@5 dengan data sintetis.
   * Pengujian mIoU dan perhitungan speedup / storage footprint.
2. **Integration Test Runner:**
   * Menjalankan runner mode `--synthetic` dengan video buatan singkat untuk memverifikasi keseluruhan alur benchmark berjalan tanpa galat dan menghasilkan tabel Markdown valid.
