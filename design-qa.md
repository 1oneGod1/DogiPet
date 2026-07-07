# Design QA — DogiPet 0.3.0

**Source visual truth**

- `I:/apps anjing/source-captures/comnyang-desktop.png` — referensi bahasa
  visual: hitam, putih, aksen kuning, tipografi pixel, border tipis, dan kartu.
- `new_frames_preview.png` — sprite Dogi asli dari ZIP pengguna.

**Implementation evidence**

- `qa/control-center-v030.png` — Control Center dari packaged `DogiPet.exe`.
- `qa/control-center-v030-comparison.png` — referensi dan implementasi dalam
  satu gambar perbandingan.
- `qa/hold-animation-v030.png` — kedua frame pose Dogi saat digendong.

**Viewport and state**

- Windows 11, display scaling 125%, 948 × 780 physical px.
- Halaman Beranda, tema Coklat, satu Dogi aktif.

**Full-view comparison evidence**

Control Center mempertahankan komposisi hitam dominan, teks putih hangat,
aksen kuning, border abu tipis, dan kartu persegi dari referensi. Versi 0.3
menambahkan navigasi Agent AI dan bar kebutuhan tanpa memecah hierarki utama.
Identitas, ikon, karakter, dan aset tetap milik DogiPet.

**Focused region comparison evidence**

`qa/hold-animation-v030.png` memperlihatkan tubuh vertikal dan perbedaan posisi
kaki antardua frame. Grid tetap 16 × 12, warna berasal dari tema Dogi, dan tidak
ada smoothing yang mengaburkan pixel.

## Findings

- Tidak ada temuan P0, P1, atau P2.
- [P3] Perbedaan ayunan kaki sengaja kecil agar animasi tidak berkedip keras
  pada tick 110 ms; bisa diperbesar pada iterasi karakter berikutnya.

## Required fidelity surfaces

- Fonts and typography: Consolas bold untuk display dan kontrol; hierarchy dan
  wrapping terbaca pada 125% scaling.
- Spacing and layout rhythm: sidebar 196 px, content 680 × 620 px, gap kartu
  12 px, dan header 76 px; semua enam halaman lolos pemeriksaan ukuran.
- Colors and visual tokens: latar `#090909`, panel `#151515`, border `#383838`,
  teks `#f5f2e9`, aksen `#f2cf45`.
- Image quality and asset fidelity: preview serta animasi hold memakai sprite
  grid asli, bukan placeholder atau aset generik.
- Copy and content: UI utama berbahasa Indonesia; nama channel dan agent tetap
  memakai istilah teknis yang mudah dikenali.

## Interactions verified

- Drag memasuki `hold`, mengunci prioritas state, membatasi posisi tetap di
  layar, dan keluar dari pose saat dilepas.
- Fetch dilanjutkan setelah selesai digendong; status agent kembali ke `think`.
- Navigasi Beranda, Tampilan, Fokus, Agent AI, Pembaruan, dan Tentang.
- Nama, tema, empat gaya suara, kebutuhan Dogi, Pomodoro, peregangan, pengingat
  istirahat, pemasangan hook Claude Code, dan auto-update.

## Verification

- 30 unit test lulus, termasuk grid hold dan transisi drag.
- Source compilation dan smoke test lulus.
- Packaged executable memiliki metadata versi `0.3.0` dan smoke test lulus.
- Visual comparison tidak memiliki mismatch P0/P1/P2.

final result: passed
