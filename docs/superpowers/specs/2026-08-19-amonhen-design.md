# AmonHen - Design Spec

> *"From the Seat of Seeing, no moment remains hidden."*

Tanggal: 2026-08-19
Status: disetujui untuk masuk ke tahap perencanaan implementasi

---

## 1. Ringkasan

AmonHen adalah CLI tool dan pustaka Python untuk mencari momen spesifik di dalam koleksi video menggunakan kueri teks bahasa alami.
Seluruh pemrosesan berjalan lokal di CPU, tanpa GPU diskrit dan tanpa layanan cloud.

Nama diambil dari Amon Hen, bukit dengan Seat of Seeing dalam *The Lord of the Rings*, tempat pandangan seseorang terbuka menembus jarak.
Metafora itu menggambarkan fungsi produk: melihat menembus durasi video yang panjang untuk melompat ke satu momen.

Pengguna sasaran adalah orang yang menyimpan video panjang di mesin sendiri dan ingin mencarinya tanpa mengunggah apa pun.

## 2. Masalah

Mencari momen di video panjang saat ini terbentur dua ekstrem.
Vision-language model besar seperti LLaVA membutuhkan VRAM 16 GB atau lebih dan terlalu lambat untuk dijalankan lokal.
Sampling frame naif tanpa penyaringan memproses ribuan frame yang hampir identik, membuat pengindeksan lama dan boros memori.

Belum ada alat ringan yang bisa dipasang dalam satu perintah, berjalan di laptop biasa, dan memberi hasil yang cukup baik untuk dipakai sehari-hari.

## 3. Keputusan lingkup

Keputusan berikut sudah dikunci melalui diskusi desain dan menjadi dasar seluruh spec ini.

**Jenis video: umum.** Tidak ada asumsi bahwa kamera diam. Konsekuensinya, deteksi gerak sederhana tidak cukup sebagai satu-satunya strategi penyaringan, dan sistem membutuhkan sampler berjenjang yang bekerja baik pada video statis maupun bergerak.

**Tujuan rilis: open-source publik.** Konsekuensinya, kualitas hasil harus dibuktikan dengan benchmark yang dapat direproduksi, dan pemasangan harus mulus di mesin orang lain.

**Cakupan kueri: objek dan pemandangan, ditambah teks di layar melalui OCR.** Sistem tidak memahami aksi atau kejadian temporal seperti "seseorang masuk ruangan", karena CLIP bekerja per frame. Batasan ini dinyatakan eksplisit di README.

**Hardware yang diuji: Windows x86 dan Linux x86.** Klaim mengenai Raspberry Pi, Jetson, atau perangkat edge lain dihapus dari seluruh materi karena tidak ada perangkat untuk mengukurnya.

**Skala: banyak video dalam satu basis data.** Pencarian berjalan lintas seluruh koleksi.

**Evaluasi: subset benchmark publik.** Charades-STA atau QVHighlights, dengan sampling tetap sebagai baseline pembanding.

**Antarmuka: sesi interaktif ditambah subcommand sekali-jalan.** Pola yang sama dengan Claude Code.

**Distribusi: PyPI lebih dulu, binari mandiri dan pembungkus npm menyusul.**

## 4. Arsitektur

### 4.1 Modul

Enam modul, masing-masing dengan satu tanggung jawab dan antarmuka yang dapat diuji sendiri.

**`amonhen.decode`** menyediakan frame dari file video.
Antarmuka: `iter_frames(path, fps_target) -> Iterator[Frame]`, di mana `Frame` membawa `ts_ms` dan array gambar.
Implementasi memakai subprocess ffmpeg dengan pipe rawvideo, bukan loop `cv2.VideoCapture`.
Alasannya, dekode adalah bottleneck sebenarnya dan filter `fps=` milik ffmpeg melakukan penjarangan di dalam dekoder, sehingga frame yang tidak dipakai tidak pernah mencapai Python.
Modul ini tidak mengetahui model maupun basis data.

**`amonhen.sample`** memutuskan frame mana yang layak dikodekan.
Antarmuka: `Sampler.keep(frame) -> bool`, bersifat stateful.
Berisi dua gerbang pertama dari tiga gerbang sistem; gerbang ketiga berada di pipeline karena membutuhkan vektor.
Setiap gerbang adalah kelas terpisah yang dapat dirangkai dan dinonaktifkan lewat konfigurasi.

**`amonhen.encode`** membungkus ONNX Runtime.
Antarmuka: `ImageEncoder.embed(frames) -> ndarray[N, D]` dan `TextEncoder.embed(text) -> ndarray[D]`.
Selalu bekerja dalam batch, karena inference INT8 di CPU sangat tidak efisien pada batch tunggal.
Modul ini menangani praproses gambar, pengunduhan model, dan cache model.
Modul ini tidak mengetahui video.

**`amonhen.ocr`** mengekstrak teks dari frame.
Antarmuka: `extract(frames) -> list[str]`.
Dijalankan pada frame yang sama yang lolos sampler, sehingga tidak ada dekode kedua.
Nonaktif secara default.

**`amonhen.store`** menangani persistensi.
Antarmuka: `add_video`, `add_frames`, `search_vector`, `search_text`, `list_videos`, `stats`.
Satu-satunya modul yang mengetahui SQL.
Backend tunggal `sqlite-vec`; FAISS tidak dipakai agar hanya ada satu jalur kode dan satu file basis data yang portabel.

**`amonhen.pipeline`** merangkai semuanya.
Antarmuka: `index(paths, config, reporter)` dan `search(query, k)`.
Ini satu-satunya tempat yang mengetahui urutan kerja, gerbang embedding, penggabungan segmen, dan penggabungan skor.

Lapis CLI (`amonhen.cli`) tipis di atas pipeline.
Aturannya, tidak ada logika di CLI yang tidak dapat dipanggil dari Python.

Arah ketergantungan satu arah: `cli` bergantung pada `pipeline`, dan `pipeline` bergantung pada modul lapis bawah. Modul lapis bawah tidak pernah saling mengimpor.

### 4.2 Alur data

```
video files
    |
    v
decode (ffmpeg pipe, penjarangan fps di dekoder)
    |
    v
sample gerbang 1: beda piksel resolusi rendah
    |
    v
sample gerbang 2: perceptual hash
    |
    v
encode (MobileCLIP2 ONNX INT8, batch)
    |
    +--> ocr (opsional, frame yang sama)
    |
    v
gerbang 3: jarak kosinus terhadap frame tersimpan terakhir
    |
    v
store (sqlite-vec + FTS5)
```

Gerbang satu dan dua menghemat waktu komputasi.
Gerbang tiga tidak menghemat waktu enkode, tetapi menekan ukuran basis data dan derau hasil pencarian.
Gerbang tiga adalah yang menyelamatkan kasus video bergerak, karena bekerja di ruang semantik dan bukan di ruang piksel.

### 4.3 Model

MobileCLIP2 dalam format ONNX. Stage 1 sampai Stage 3 memakai varian FP32 (S0, 286 MB gabungan vision dan text), karena percobaan kuantisasi INT8 dinamis merusak output pada layer Conv yang mendominasi bobot model - lihat temuan terukur di bagian 14.
Kuantisasi INT8 yang aman membutuhkan kalibrasi statis dengan sampel gambar nyata, dijadwalkan sebagai task benchmark di Stage 4 dan dibandingkan terhadap baseline FP32.

Untuk OCR digunakan engine ONNX ringan seperti RapidOCR.

Identitas model disimpan di basis data agar pergantian model terdeteksi dan tidak mencampur embedding dari dua model berbeda dalam satu indeks.

## 5. Skema basis data

Lokasi default `~/.amonhen/index.db`, dapat ditimpa dengan opsi `--db`.

```sql
video(id, path, path_hash, duration_ms, fps, size_bytes, mtime,
      indexed_at, sampler_config_hash, model_id, score_baseline)

frame(id, video_id, ts_ms, kept_reason, ocr_text)

vec_frame(frame_id, embedding float[512])   -- tabel virtual sqlite-vec

fts_ocr(frame_id, ocr_text)                 -- tabel virtual FTS5
```

Kombinasi `path_hash`, `mtime`, dan `size_bytes` menangani pengindeksan inkremental.
Video yang tidak berubah dilewati; video yang berubah dihapus dari indeks lalu diindeks ulang.

`sampler_config_hash` dan `model_id` memicu pengindeksan ulang ketika konfigurasi atau model berganti.
Tanpa penjagaan ini, indeks dapat berisi campuran embedding yang tidak sebanding, dan gejalanya sangat sulit dilacak.

`kept_reason` mencatat gerbang mana yang meloloskan sebuah frame.
Kolom ini membuat klaim efisiensi dapat diaudit, karena perintah `stats` dapat melaporkan proporsi frame yang dibuang tiap tahap.

`score_baseline` menyimpan hasil kalibrasi ambang, dijelaskan di bagian berikutnya.

## 6. Pencarian dan penilaian

Alur kueri:

1. Teks kueri dikodekan sekali menjadi vektor.
2. Pencarian KNN pada `vec_frame` mengambil `k * 8` frame kandidat lintas seluruh video.
3. Bila OCR aktif, FTS5 dicari secara paralel. Skornya dinormalisasi lalu digabungkan dengan skor kosinus memakai bobot yang dapat disetel, dengan default berat pada CLIP.
4. Frame kandidat dikelompokkan per video dan digabungkan menjadi segmen. Frame yang berjarak kurang dari ambang waktu tertentu menyatu, skor segmen diambil dari frame terbaiknya, dan panjang segmen dibatasi.
5. Segmen diurutkan lalu dipotong ke `k` teratas.

Setiap hasil berisi path video, rentang waktu, skor, dan frame perwakilan.

### 6.1 Kalibrasi ambang

Kueri yang isinya tidak ada di dalam koleksi harus mengembalikan hasil kosong, bukan lima hasil yang tidak relevan.

Skor kosinus CLIP mentah tidak dapat dipakai sebagai ambang absolut karena rentang nilainya bergeser antar model dan antar domain video.
Karena itu ambang ditentukan secara relatif.
Setelah pengindeksan selesai, sistem mengambil sampel acak frame dari indeks, menghitung distribusi skor terhadap sekumpulan kueri acak, dan menyimpan statistik dasarnya di kolom `score_baseline`.
Saat kueri dijalankan, kandidat yang tidak menonjol secara statistik terhadap baseline itu dibuang.

Ini bagian paling rawan salah di seluruh sistem.
Nilai parameternya tidak boleh dikunci sebelum diuji lewat harness benchmark.

## 7. Antarmuka pengguna

### 7.1 Bentuk

Menjalankan `amon-hen` tanpa argumen membuka sesi interaktif.
Prompt berada di bawah, hasil mengalir ke atas seperti percakapan, bukan layout panel tetap.

Hasil ditampilkan sebagai daftar bernomor berisi nama video, rentang waktu, skor sebagai bar visual, dan potongan teks OCR bila ada.
Riwayat kueri dapat dinavigasi dengan tombol panah dan tersimpan antar sesi.
Perintah sesi diawali garis miring: `/index`, `/videos`, `/stats`, `/config`, `/help`, `/exit`.
Menekan Enter pada nomor hasil membuka video di pemutar sistem pada timestamp tersebut.

Mode sekali-jalan tetap warga kelas satu: `index`, `search`, `stats`, `videos`, `setup`.
Setiap perintah menyediakan opsi `--json` yang mematikan seluruh dekorasi dan mencetak JSON murni.
Pesan untuk manusia dikirim ke stderr dan data dikirim ke stdout, sehingga keluaran dapat dipipe.

### 7.2 Progres

Indikator progres punya dua tingkat: satu bar untuk keseluruhan daftar video, dan satu bar per video.
Angka yang ditampilkan mencakup frame terdekode, frame dipertahankan, persentase dibuang, kecepatan relatif terhadap realtime, dan perkiraan sisa waktu.
Tampilan ini sama di mode interaktif maupun sekali-jalan.

### 7.3 Tema

Prinsipnya, tema hidup di bingkai dan bukan di data.
Nama perintah, path, timestamp, dan angka tetap polos agar dapat dipipe dan dibaca mesin.

Banner ASCII muncul sekali per sesi, maksimal enam baris, berisi judul, tagline, dan baris status yang memuat versi, model aktif, jumlah video terindeks, dan ukuran basis data.
Banner tidak pernah muncul di mode sekali-jalan dan tidak pernah muncul ketika output bukan TTY.

Palet warna terdiri dari abu batu untuk teks dasar, emas pudar untuk satu penyorotan per layar, hijau lumut untuk keberhasilan, merah karat untuk galat, dan biru pucat untuk metadata.
Kontras diverifikasi pada latar terang dan gelap.

Pemisahan antar blok memakai ruang kosong, bukan garis.
Tabel tidak berbingkai, hanya kolom yang dirapikan.

Teks bernada Tolkien dipakai di banner, hasil kosong, ringkasan pengindeksan selesai, layar bantuan, dan pesan keluar.
Selama pengindeksan dan pencarian, baris status memakai kata kerja bertema yang dipilih acak dari kumpulan dan berganti tiap beberapa detik.
Kumpulan ini berisi sekitar tiga puluh sampai empat puluh kata, dipisah menjadi kumpulan untuk pengindeksan dan kumpulan untuk pencarian, dan disimpan dalam satu file data terpisah agar mudah ditambah lewat kontribusi.
Kata kerja berputar hanya menempati satu baris dan tidak pernah menggeser angka kerja yang ada di baris yang sama.

Pesan galat selalu polos, tanpa versi bernada, karena pengguna yang sedang mencari masalah tidak boleh disuruh menerjemahkan prosa.

Seluruh tema nonaktif ketika opsi `--plain` diberikan, ketika `NO_COLOR` diset, ketika `--json` dipakai, dan ketika output bukan TTY.
Mematikan tema hanya menghilangkan banner dan warna; tata letaknya tetap identik.
Sifat ini adalah ujian bahwa tema benar-benar aksen dan bukan tulang punggung tampilan.

### 7.4 Batas arsitektur UI

Pipeline menerima objek reporter progres dan memanggil metodenya.
Pipeline tidak pernah mengetahui pustaka rendering yang dipakai.

Reporter punya tiga implementasi: satu berbasis Rich untuk terminal, satu senyap untuk mode JSON, dan satu perekam untuk pengujian.
Implementasi perekam inilah yang memungkinkan seluruh alur diuji tanpa terminal sungguhan.

Ketergantungan UI terbatas pada `rich` untuk rendering, `prompt_toolkit` untuk baris input dan riwayat, serta `typer` untuk parsing argumen.

## 8. Distribusi

Paket PyPI bernama `amonhen`, dipasang melalui `uv tool install amonhen` atau `pipx install amonhen`.
Wheel murni Python tanpa kompilasi.

Dua sumber gesekan ditangani secara eksplisit, karena keduanya adalah penyebab paling umum kegagalan adopsi alat sejenis.

ffmpeg tidak tersedia di sebagian besar mesin Windows.
Paket `imageio-ffmpeg` disertakan sebagai dependensi karena membawa biner ffmpeg statis untuk tiap platform.
Bila pengguna sudah memiliki ffmpeg di PATH, biner itu yang dipakai.
Pengguna tidak pernah diminta memasang apa pun secara manual.

Berkas model tidak disertakan dalam wheel.
Model diunduh saat pertama dipakai ke `~/.amonhen/models/`, disertai bar progres, verifikasi checksum, dan keterangan ukuran unduhan.
Perintah `amon-hen setup` memicu pengunduhan secara manual untuk keperluan pemasangan luring.

Ukuran keberhasilan lapis ini: perintah pertama yang dijalankan pengguna baru berhasil tanpa perlu membaca dokumentasi.

Binari mandiri hasil PyInstaller dan pembungkus npm yang mengunduhnya dijadwalkan setelah rilis pertama, sebagai tahap terpisah.
Menggabungkannya ke rilis pertama berarti men-debug PyInstaller dan men-debug pipeline pada waktu bersamaan.

## 9. Pengujian

Pengembangan mengikuti test-driven development: pengujian ditulis lebih dulu, dijalankan sampai terlihat gagal, baru implementasi ditulis.

Pengujian unit menguji tiap modul dengan input buatan.
Sampler diuji dengan array gambar sintetis, store diuji dengan vektor acak, dan encoder diuji dengan objek ONNX tiruan.
Lapis ini tidak membutuhkan file video maupun berkas model, sehingga selesai dalam hitungan detik.

Pengujian integrasi memakai video sintetis yang dihasilkan ffmpeg saat pengujian berjalan, berupa beberapa detik pola warna dan gerakan dengan sifat yang diketahui pasti.
Lapis ini memverifikasi keseluruhan alur dari dekode sampai pencarian.

Pengujian CLI memakai reporter perekam untuk memastikan keluaran `--json` benar-benar bersih dan keluaran non-TTY tidak mengandung kode escape warna.

## 10. Benchmark

Harness benchmark adalah skrip terpisah, bukan bagian dari suite pengujian.

Harness membandingkan sampler adaptif melawan sampling tetap pada subset Charades-STA, mengukur Recall@1, Recall@5, mIoU, waktu pengindeksan, penggunaan RAM puncak, dan ukuran basis data.
Keluarannya berupa tabel Markdown yang dapat langsung ditempel ke README.

Aturan yang mengikat: setiap klaim numerik di README harus memiliki baris asalnya di keluaran harness ini.

## 11. Urutan pengiriman

Setiap tahap menghasilkan sesuatu yang dapat dijalankan.

1. **Inti.** Dekode, enkode, store, sampling tetap, serta perintah `index` dan `search` sekali-jalan. Belum ada tema maupun sampler adaptif.
2. **Sampler adaptif.** Tiga gerbang, perintah `stats`, dan angka pembanding pertama.
3. **Kualitas hasil.** Penggabungan segmen dan kalibrasi ambang. Di tahap inilah pencarian berubah dari demo menjadi alat.
4. **Benchmark.** Harness evaluasi, angka, dan tabel README.
5. **Antarmuka.** Sesi interaktif, banner, tema, dan kata kerja berputar.
6. **OCR.** Jalur indeks kedua dan penggabungan skor.
7. **Rilis.** Packaging, penanganan ffmpeg dan unduhan model, uji pemasangan bersih di Windows dan Linux, README, dan rilis PyPI.
8. **Binari mandiri.** PyInstaller di CI, GitHub Releases, dan pembungkus npm. Setelah v1 terbukti.

Antarmuka sengaja ditempatkan setelah kualitas hasil, karena tampilan yang baik di atas pencarian yang buruk hanya menyembunyikan masalah.
OCR ditempatkan di belakang karena merupakan jalur paling terisolasi, sehingga dapat digeser ke rilis berikutnya tanpa mengubah bagian lain.

## 12. Di luar lingkup

Pemahaman aksi dan kejadian temporal berada di luar lingkup, karena membutuhkan model video-temporal yang tidak realistis dijalankan di CPU.

Pengenalan wajah dan identifikasi orang tidak disertakan.

Antarmuka web, mode server, dan pemrosesan terdistribusi tidak disertakan.

Backend FAISS tidak disertakan selama `sqlite-vec` masih memadai.

Dukungan GPU tidak disertakan; menjalankan seluruhnya di CPU adalah inti dari proposisi produk ini.

## 13. Catatan hukum

Nama tempat, kosakata umum, dan tagline yang ditulis sendiri dengan gaya bertema aman untuk proyek open-source non-komersial.
Yang perlu dihindari adalah kutipan langsung dari buku maupun film, dan penggunaan aset visual resmi.

## 14. Risiko yang perlu diverifikasi lebih dulu

**Terukur (2026-08-19).** MobileCLIP2 ONNX INT8 resmi tidak tersedia di mana pun yang ditemukan. Model default v1 adalah `plhery/mobileclip2-onnx`, varian S0, FP32: vision encoder `onnx/s0/vision_model.onnx` (44 MB), text encoder `onnx/s0/text_model.onnx` (242 MB), tokenizer `tokenizer.json`. Diukur langsung dari file: `embed_dim=512`, `image_size=256`, input vision `pixel_values` bentuk `(batch,3,256,256)`, output `image_embeds` bentuk `(batch,512)`, input text `input_ids` bentuk `(batch,77)` tanpa attention mask, output `text_embeds` bentuk `(batch,512)`.

Percobaan kuantisasi INT8 dinamis dilakukan dan ditolak. Arsitektur vision encoder didominasi 95 layer `Conv` (kemungkinan besar blok MobileOne/depthwise) dan hanya 8 layer `MatMul`. Mengkuantisasi `Conv` secara dinamis (dengan maupun tanpa `per_channel`) menghasilkan cosine similarity mendekati nol terhadap output FP32 - modelnya rusak, bukan sekadar kurang akurat. Membatasi kuantisasi ke `MatMul` saja menjaga cosine similarity di atas 0.999, tapi ukuran model nyaris tak berkurang (44 MB menjadi 36 MB) karena mayoritas bobot ada di `Conv`. Total ukuran FP32 (vision + text) adalah 286 MB, jauh dari target awal 50-80 MB.

Kesimpulan: kuantisasi Conv yang aman membutuhkan kuantisasi statis dengan kalibrasi memakai sampel gambar nyata, bukan kuantisasi dinamis. Ini pekerjaan pengukuran sungguhan, dipindah ke Stage 4 sebagai task benchmark tersendiri, dibandingkan terhadap baseline FP32 dengan Recall@1/Recall@5/mIoU. Stage 1 sampai Stage 3 dibangun di atas model FP32.

Kecepatan dekode kemungkinan besar mendominasi waktu pengindeksan, bukan inference. Rasio keduanya harus diukur terpisah sebelum target kecepatan apa pun dicantumkan.

Kebutuhan memori sebenarnya perlu diukur sebelum angka RAM apa pun ditulis di README. Target 512 MB yang muncul di draf awal kemungkinan besar tidak realistis.
