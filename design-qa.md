# Design QA — DogiPet 0.5.0

**Source visual truth**

- `assets/reference/dogi-clean-sprite-sheet-v050.png` — lembar sprite bersih
  hasil rekreasi dari dua referensi pengguna, 4 kolom × 17 state.
- `C:/Users/Andi Purba/Downloads/3ddea762-ed69-4fbf-a598-bea4ae85e14e.png`
  — referensi khusus pose pusing.

**Implementation evidence**

- `qa/sprite-sheet-comparison-v050.png` — source dan seluruh sprite hasil impor
  ditampilkan bersama.
- `qa/dizzy-comparison-v050.png` — source pose pusing dan render aplikasi pada
  state yang sama.
- `qa/dizzy-implementation-v050.png` — render dari packaged-style Tk canvas
  melalui opsi QA `--opaque-preview --state=dizzy`.
- `qa/control-center-sprites-v050.png` — sprite baru pada Preview Langsung.

**Viewport and state**

- Windows 11, display scaling 125%.
- Pet viewport 230 × 176 logical px; state `dizzy`.
- Full sheet: 17 state, masing-masing 4 frame.

**Full-view comparison evidence**

`qa/sprite-sheet-comparison-v050.png` menunjukkan siluet, arah hadap, laptop,
panah scroll, monitor meeting, tanda tanya, spiral pusing, dan karakter Dogi
tetap konsisten setelah dipotong ke canvas aplikasi. Ruang vertikal tambahan
pada atlas implementasi disengaja agar semua state memakai viewport 160 × 140
tanpa perubahan posisi jendela desktop.

**Focused region comparison evidence**

`qa/dizzy-comparison-v050.png` membandingkan frame pusing pertama pada density
Windows yang sama. Kepala miring, spiral, tanda tambah, lidah, outline, dan
palet terbawa ke render Tk tanpa checkerboard, fringe hijau, blur, atau crop.

## Findings

- Tidak ada temuan P0, P1, atau P2.
- Tidak ada P3 yang menghalangi handoff.

## Required fidelity surfaces

- Fonts and typography: sprite tidak memakai tipografi; label Control Center
  tetap memakai Consolas dan tidak berubah.
- Spacing and layout rhythm: semua frame memakai canvas 160 × 140, baseline
  bawah konsisten, dan muat dalam pet window 230 × 176.
- Colors and visual tokens: palet cokelat referensi dipertahankan; lima tema
  tambahan dihasilkan dari mapping fur-only sehingga laptop, panah, monitor,
  mata, dan lidah tidak berubah warna.
- Image quality and asset fidelity: PNG RGBA memakai alpha nyata, tepi pixel
  keras, karakter/props lengkap, tanpa checkerboard dan tanpa placeholder.
- Copy and content: pesan reaksi “Waduh... pusing!” memakai Bahasa Indonesia
  dan hanya tampil saat gesture terdeteksi.

## Interactions verified

- Dogi menoleh sesuai arah gerak horizontal kursor saat idle/walk/happy.
- Empat pembalikan dengan lintasan minimal 55 px dalam 2,6 detik memicu state
  `dizzy` selama sekitar 4,8 detik.
- Gerakan kecil/jitter tidak memicu pusing dan cooldown delapan detik mencegah
  animasi berulang tanpa jeda.
- State drag, fetch, agent thinking, serta meeting alert/watch tidak ditimpa
  oleh gesture pusing.
- Sprite digendong, mengetik, scroll, meeting, tidur, makan, dan variasi gerak
  lain ikut berpindah ke aset bersih empat frame.

## Verification

- 41 unit test lulus, termasuk detektor gesture, false-positive jitter,
  integrasi state pusing, kelengkapan 816 aset tema/arah, dan alpha PNG.
- PyInstaller, executable smoke, installer silent, installed-app smoke, dan
  uninstall berhasil.
- `DogiPet.exe` dan `DogiPet-Setup.exe` memiliki ProductVersion `0.5.0`.

final result: passed
