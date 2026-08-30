# AmonHen Stage 5 (Interactive Interface & Tolkien Theme) - Design Spec

> *"From the Seat of Seeing, no moment remains hidden."*

Tanggal: 2026-08-26  
Status: Disetujui (Tahap Perancangan Selesai)

---

## 1. Ringkasan

Dokumen ini mendefinisikan desain teknis untuk **Stage 5: Antarmuka Interaktif TUI & Tema Tolkien** pada AmonHen.
Tahap ini menghadirkan antarmuka percakapan interaktif (REPL), rendering Rich terminal yang elegan dengan tema Tolkien, live progress bar dua tingkat saat indexing, dan fungsionalitas melompat membuka pemutar video pada timestamp yang ditemukan.

Tujuan utama:
1. **Interactive REPL Session:** Menjalankan `amon-hen` tanpa argumen membuka prompt interaktif berbasis `prompt_toolkit` dengan riwayat tersimpan di `~/.amonhen/history` dan navigasi panah `↑`/`↓`.
2. **Slash Command Handling:** Mendukung perintah slash: `/open <nomor>`, `/index <path>`, `/videos`, `/stats`, `/help`, `/exit`.
3. **Media Player Launching:** Membuka pemutar video sistem di detik `best_ts_ms` menggunakan player pintar (`mpv`, `vlc`, `ffplay`) atau fallback default OS (`os.startfile` / `xdg-open`).
4. **Dual-Level Rich Progress Reporting:** Menampilkan progress bar dua tingkat (Overall Video Progress + Current Video Frame Progress) dengan kecepatan $X\times$ RT dan rasio pemangkasan frame.
5. **Tema Tolkien & Turning Verbs:** Banner ASCII *Seat of Seeing*, palet warna bernuansa batu & emas pudar, dan baris status kata kerja berputar (*surveying*, *discerning*, *seeking*, *unveiling*).

---

## 2. Struktur Modul & Komponen

```
src/amonhen/
├── player.py         # Deteksi & eksekusi pemutar video dengan seek timestamp
├── theme.py          # Definisi gaya warna Rich, banner ASCII, & kata kerja berputar
├── progress.py       # Menambahkan RichReporter yang mengimplementasikan protokol Reporter
├── interactive.py    # Loop sesi interaktif REPL prompt_toolkit
└── cli.py            # Routing: amon-hen tanpa argumen memanggil interactive.run_session()
```

---

## 3. Spesifikasi Fungsional

### 3.1 Media Player Launcher (`player.py`)

Fungsi `open_video_at(video_path: Path | str, ts_ms: int) -> bool`:
1. Konversi `ts_s = ts_ms / 1000.0`.
2. Cek ketersediaan pemutar media di `PATH`:
   * `mpv`: `mpv --start=<ts_s> <video_path>`
   * `vlc`: `vlc --start-time=<ts_s> <video_path>`
   * `ffplay`: `ffplay -ss <ts_s> <video_path>`
3. Jika tidak ditemukan, gunakan fallback OS:
   * Windows: `os.startfile(video_path)`
   * Linux: `subprocess.Popen(["xdg-open", str(video_path)])`
4. Menangani kesalahan tanpa menyebabkan sesi REPL crash.

### 3.2 Tema & Kata Kerja Berputar (`theme.py`)

* **Palet Warna:**
  * Base text: `#A0A0A0` (stone gray)
  * Highlight / Bar: `#E5C07B` (muted gold)
  * Success: `#98C379` (moss green)
  * Error: `#E06C75` (rust red)
  * Metadata / Time: `#61AFEF` (pale blue)
* **Turning Verbs:**
  Kumpulan kata kerja bertema (e.g. *gazing*, *watching*, *surveying*, *discerning*, *seeking*, *scouring*, *unveiling*, *delving*, *glimpsing*, *perceiving*) yang berotasi pada status bar.
* **Plain Mode:** Jika opsi `--plain`, variabel lingkungan `NO_COLOR` diset, atau stdout bukan TTY, semua styling dan banner dinonaktifkan secara transparan.

### 3.3 Dual-Level Rich Progress Reporter (`progress.py`)

Mengimplementasikan protokol `Reporter`:
* **Bar 1 (Overall):** Jumlah video yang telah selesai / total video.
* **Bar 2 (Video Aktif):** Persentase durasi video yang terdekode, frame disimpan vs dibuang, rasio kecepatan realtime ($X\times$ RT), dan ETA.

### 3.4 Sesi Interaktif REPL (`interactive.py`)

* **Prompt:** `amon-hen> ` dengan autocomplete perintah slash dasar.
* **Cache Hasil Terakhir:** Sesi menyimpan `last_results: list[Segment]`.
* **Perintah:**
  * Kueri teks (e.g. `a person holding an umbrella`): Melakukan pencarian dan menampilkan tabel segmen dengan visual score bar.
  * `/open <nomor>` (e.g. `/open 1` atau `/1`): Membuka video pada segmen peringkat tersebut.
  * `/index <path>`: Menjalankan pipeline indexing dengan RichReporter.
  * `/videos`: Menampilkan daftar video terindeks.
  * `/stats`: Menampilkan statistik frame dan filtering reason.
  * `/help`: Menampilkan panduan ringkas.
  * `/exit` atau `/quit` (atau `Ctrl-D` / `Ctrl-C`): Keluar dari sesi.

---

## 4. Rencana Pengujian (`tests/`)

1. **`tests/test_player.py`:**
   * Verifikasi pembentukan argumen CLI untuk mpv/vlc/ffplay.
   * Verifikasi eksekusi fallback OS saat tidak ada player khusus.
2. **`tests/test_theme.py`:**
   * Verifikasi formatting banner dan rotasi kata kerja.
   * Verifikasi perilaku saat `NO_COLOR` / plain mode aktif.
3. **`tests/test_progress.py`:**
   * Verifikasi `RichReporter` merespons callback event pipeline dengan benar tanpa exception.
4. **`tests/test_interactive.py`:**
   * Pengujian parser perintah slash (`/open`, `/help`, `/exit`).
   * Pengujian routing kueri pencarian dan caching `last_results`.
