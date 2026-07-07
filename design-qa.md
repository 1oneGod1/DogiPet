# Design QA — DogiPet 0.1.0

**Source visual truth**

- `new_frames_preview.png` — sprite Dogi yang disediakan dalam ZIP.
- `I:/apps anjing/source-captures/comnyang-desktop.png` — referensi konsep dan daftar perilaku produk, bukan aset yang disalin.

**Implementation evidence**

- `qa/implementation-dogipet.png` — jendela dari executable PyInstaller yang sedang berjalan.
- `qa/comparison.png` — sprite sumber dan hasil executable dalam satu gambar perbandingan.

**Viewport and state**

- Windows 11, scaling 125%.
- Jendela logis Tkinter 230 × 96 px; hasil `PrintWindow` 184 × 77 physical px.
- Tema Shiba, state idle, menghadap kanan.

**Full-view comparison evidence**

Komposisi karakter, siluet, warna Shiba, outline cokelat, moncong krem,
mata, hidung, dan lidah konsisten dengan sprite sumber. Area hitam pada capture
adalah representasi transparansi oleh `PrintWindow`; saat aplikasi tampil di
desktop Windows, warna transparan tidak terlihat.

**Focused region comparison evidence**

Tidak diperlukan crop tambahan karena seluruh aset karakter hanya 16 × 12
pixel dan semua detail utama sudah terbaca pada `qa/comparison.png`.

## Findings

- Tidak ada temuan P0, P1, atau P2.
- [P3] Capture native tidak dapat memperlihatkan transparansi desktop.
  Ini keterbatasan metode capture, bukan perbedaan pada aplikasi yang berjalan.

## Required fidelity surfaces

- Fonts and typography: bubble memakai Consolas bold agar tetap selaras dengan
  karakter pixel; tidak ada bubble pada state idle yang dibandingkan.
- Spacing and layout rhythm: sprite tetap memakai grid 16 × 12, scale 5,
  dengan ruang bubble 36 px seperti implementasi sumber.
- Colors and visual tokens: tema Shiba dan fixed colors berasal langsung dari
  palet prototype ZIP.
- Image quality and asset fidelity: sprite dirender sebagai blok pixel tanpa
  smoothing; ikon aplikasi dibuat dari frame Dogi yang sama, bukan aset generik.
- Copy and content: label menu, pesan Pomodoro, peregangan, updater, dan status
  agent menggunakan Bahasa Indonesia yang konsisten.

## Patches made during QA

- Menambahkan DPI awareness agar koordinat kursor dan posisi Dogi konsisten pada
  Windows dengan display scaling.
- Menyesuaikan callback `pynput` 1.8.2 untuk parameter event Windows terbaru.
- Menambahkan smoke-test mode untuk memvalidasi executable dan hasil installer.
- Menambahkan ikon hasil render sprite Dogi ke executable dan installer.

## Verification

- 5 unit test updater lulus.
- Python compilation lulus.
- PyInstaller executable smoke test lulus.
- Installer, aplikasi hasil instalasi, dan uninstaller smoke test lulus.

final result: passed
