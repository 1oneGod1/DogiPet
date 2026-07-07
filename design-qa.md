# Design QA — DogiPet 0.5.3

**Source visual truth**

- `new_frames_preview.png` — referensi kepadatan pixel asli dari pengguna.
- `assets/reference/dogi-chunky-sprite-sheet-v051.png` — lembar sprite chunky
  hasil rekreasi, diproses ke grid logis yang sama dengan renderer lama.
- `C:/Users/Andi Purba/Downloads/3ddea762-ed69-4fbf-a598-bea4ae85e14e.png`
  — referensi khusus pose pusing.

**Implementation evidence**

- `qa/sprite-sheet-comparison-v051.png` — source dan seluruh sprite hasil impor
  ditampilkan bersama.
- `qa/pixel-density-comparison-v051.png` — referensi lama dan tiga baris sprite
  baru dalam satu comparison input.
- `qa/pixel-density-implementation-v051.png` — render Tk dari state `idle`
  melalui opsi QA `--opaque-preview --state=idle`.
- `qa/think-animation-v052.png` — urutan ping-pong bingung yang dipakai app.
- `qa/walk-right-v052.png` dan `qa/run-right-v052.png` — frame sumber-kiri
  setelah dicerminkan untuk gerakan ke kanan.
- `qa/type-animation-v053.png` — strip mengetik baru dengan delapan frame,
  tubuh/laptop stabil, paw bergantian, dan pose penutup sama dengan pose awal.

**Viewport and state**

- Windows 11, display scaling 125%.
- Pet viewport 230 × 176 logical px; state `idle`.
- Full sheet: 17 state, masing-masing 4 frame.

**Full-view comparison evidence**

`qa/sprite-sheet-comparison-v051.png` menunjukkan siluet, arah hadap, laptop,
panah scroll, monitor meeting, tanda tanya, spiral pusing, dan karakter Dogi
tetap konsisten setelah dipotong ke canvas aplikasi. Ruang vertikal tambahan
pada atlas implementasi disengaja agar semua state memakai viewport 160 × 140
tanpa perubahan posisi jendela desktop.

**Focused region comparison evidence**

`qa/pixel-density-comparison-v051.png` membandingkan referensi lama dan sprite
baru. Setiap frame baru diturunkan ke canvas logis 32 × 28 lalu diperbesar
nearest-neighbor; setiap blok warna tepat 5 × 5 px, sama dengan konstanta
`SCALE = 5` renderer lama. Tidak ada checkerboard, fringe hijau, blur, atau crop.

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
- Image quality and asset fidelity: PNG RGBA memakai alpha nyata; seluruh blok
  5 × 5 seragam, tepi keras, karakter/props lengkap, tanpa checkerboard.
- Copy and content: pesan reaksi “Waduh... pusing!” memakai Bahasa Indonesia
  dan hanya tampil saat gesture terdeteksi.

## Interactions verified

- Dogi menoleh sesuai arah gerak horizontal kursor saat idle/walk/happy.
- Walk, chase, dan fetch memakai metadata arah sumber-kiri; sprite dicerminkan
  ketika koordinat bergerak ke kanan sehingga kepala selalu menuju target.
- Animasi bingung memakai urutan `0,1,2,3,2,1`, tiap frame ditahan dua tick;
  transisi siklus tidak lagi melompat dari frame terakhir ke pertama.
- Arah visual walk/chase/fetch dicatat dari delta `x` aktual setiap tick; arah
  target atau kursor tidak dapat membuat sprite tampak berjalan mundur.
- Mengetik memakai delapan frame konsisten dan mempertahankan state `type`
  selama input aktif, tanpa satu frame idle saat timer internal diperbarui.
- Empat pembalikan dengan lintasan minimal 55 px dalam 2,6 detik memicu state
  `dizzy` selama sekitar 4,8 detik.
- Gerakan kecil/jitter tidak memicu pusing dan cooldown delapan detik mencegah
  animasi berulang tanpa jeda.
- State drag, fetch, agent thinking, serta meeting alert/watch tidak ditimpa
  oleh gesture pusing.
- Sprite digendong, mengetik, scroll, meeting, tidur, makan, dan variasi gerak
  lain ikut berpindah ke aset bersih empat frame.

## Verification

- 48 unit test lulus, termasuk detektor gesture, false-positive jitter,
  integrasi state pusing, kelengkapan 816 aset tema/arah, alpha PNG, dan
  pemeriksaan keseragaman setiap blok 5 × 5 px.
- PyInstaller, executable smoke, installer silent, installed-app smoke, dan
  uninstall berhasil.
- `DogiPet.exe` dan `DogiPet-Setup.exe` memiliki ProductVersion `0.5.3`.

final result: passed
