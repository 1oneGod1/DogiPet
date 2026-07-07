# Design QA — DogiPet 0.2.0

**Source visual truth**

- `I:/apps anjing/source-captures/comnyang-desktop.png` — referensi bahasa
  visual: hitam, putih, aksen kuning, tipografi pixel, border tipis, dan layout
  kartu yang tegas.
- `new_frames_preview.png` — sprite Dogi asli dari ZIP pengguna.

**Implementation evidence**

- `qa/control-center-v020.png` — Control Center native yang sedang berjalan.
- `qa/control-center-comparison.png` — referensi dan implementasi dalam satu
  gambar perbandingan.
- `qa/implementation-dogipet.png` — desktop pet dari executable.

**Viewport and state**

- Windows 11, display scaling 125%, 948 × 680 physical px.
- Halaman Beranda, tema Shiba, satu Dogi aktif.

**Full-view comparison evidence**

Control Center memakai komposisi hitam dominan, putih hangat, aksen kuning,
tipografi monospace tebal, border abu tipis, dan kartu persegi yang konsisten
dengan referensi. Implementasi tidak menyalin logo atau aset Comnyang; karakter,
ikon, dan identitas tetap DogiPet.

**Focused region comparison evidence**

`qa/control-center-comparison.png` memperlihatkan header, hierarki judul,
penggunaan aksen, karakter pixel, sidebar, dan tombol aksi pada ukuran yang
cukup untuk menilai detail utama. Tidak diperlukan crop tambahan.

## Findings

- Tidak ada temuan P0, P1, atau P2.
- [P3] Control Center memakai Consolas sebagai font pixel-native terdekat agar
  tidak menambah font eksternal ke installer. Bentuknya sedikit lebih tipis
  daripada display font pada situs referensi, tetapi hierarki dan keterbacaan
  tetap kuat.

## Required fidelity surfaces

- Fonts and typography: Consolas bold untuk display dan kontrol; hierarchy,
  wrapping, line-height, serta kontras terbaca pada 125% scaling.
- Spacing and layout rhythm: sidebar 196 px, content 680 px, kartu dan gap 12 px,
  serta header 76 px membentuk ritme yang konsisten tanpa clipping.
- Colors and visual tokens: latar `#090909`, panel `#151515`, border `#383838`,
  teks `#f5f2e9`, aksen `#f2cf45`.
- Image quality and asset fidelity: preview memakai frame Dogi asli 16 × 12 dan
  nearest-neighbor pixel blocks, bukan placeholder atau aset generik.
- Copy and content: seluruh UI utama memakai Bahasa Indonesia; nama channel
  GitHub tetap mengikuti istilah teknis `CONTINUOUS` dan `STABLE`.

## Interactions verified

- Navigasi Beranda, Tampilan, Fokus, Pembaruan, dan Tentang.
- Simpan nama, ganti warna, elus, beri tulang, tambah teman, dan tidur.
- Pomodoro, pengingat peregangan, auto-update, channel update, dan cek update.
- Sembunyikan Control Center dan buka kembali melalui klik kanan Dogi.

## Patches made during QA

- Memperbaiki capture DPI-aware agar evaluasi tidak salah menganggap panel
  kanan terpotong pada display scaling 125%.
- Menambahkan ikon Dogi nyata ke title bar dan bundle PyInstaller.
- Mengganti copy Control Center ke Bahasa Indonesia.
- Menghapus glyph swatch dan mempertahankan warna tema sebagai state tombol.

## Verification

- Unit test updater lulus.
- Source smoke test dan Control Center interaction test lulus.
- Capture berasal dari `DogiPet.exe` hasil PyInstaller, bukan source preview.
- Installer, aplikasi hasil instalasi, dan uninstaller smoke test lulus.
- Visual comparison tidak memiliki mismatch P0/P1/P2.

final result: passed
