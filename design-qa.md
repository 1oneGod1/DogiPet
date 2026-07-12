# Design QA — DogiPet 1.1.0

**Source visual truth**

- `C:/Users/ANDIPU~1/AppData/Local/Temp/codex-clipboard-7c5b2a82-47a4-460f-981b-1f260b7dd8ce.png`
  — referensi final yang dipilih pengguna: kuping tegak, badan tidak oval,
  ekor runcing, dan kepadatan pixel rendah.
- `scripts/draw_sprites.py` — sumber visual canonical, digambar manual sebagai
  template grid 32 × 28 dan dirender nearest-neighbor ke PNG transparan.
- `new_frames_preview.png` — referensi kepadatan pixel awal dari pengguna.
- `C:/Users/Andi Purba/Downloads/3ddea762-ed69-4fbf-a598-bea4ae85e14e.png`
  — referensi khusus pose pusing.

**Implementation evidence**

- `qa/all-states-preview.png` — audit cepat satu frame untuk semua 22 state,
  memastikan tidak ada pose yang kembali ke model lama.
- `qa/handmade-sprites.png` — contact sheet penuh semua frame hasil generator
  grid tangan, termasuk ekor runcing dua fase dan pose tidur tanpa gelung.
- `qa/think-animation-v052.png` — urutan ping-pong bingung yang dipakai app.
- `qa/walk-right-v052.png` dan `qa/run-right-v052.png` — frame sumber-kiri
  setelah dicerminkan untuk gerakan ke kanan.
- `qa/handmade-sprites.png` — strip mengetik 16 frame dengan keyboard mandiri,
  paw bergantian, empat tahap merah wajah, serta scroll dengan laptop + mouse.
- `qa/behaviors-v054.png` — empat tingkah spontan baru: curious, tail wag,
  beg, dan zoomies.

**Viewport and state**

- Windows 11, display scaling 125%.
- Pet viewport 230 × 176 logical px; state `idle`.
- Full sheet: 22 state; 21 state memakai 4 frame dan mengetik memakai 16 frame.

**Full-view comparison evidence**

`qa/all-states-preview.png` menunjukkan siluet, arah hadap, laptop, panah
scroll, gonggongan meeting, tanda tanya, pusing, digendong, tidur, dan karakter
Dogi tetap konsisten memakai model low-pixel baru. Semua state memakai viewport
160 × 140 tanpa perubahan posisi jendela desktop.

**Focused region comparison evidence**

Setiap frame generator berada pada canvas logis 32 × 28 lalu diperbesar
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

- Gerak kursor biasa memicu `glance`: pupil memilih kiri/atas/kanan tanpa
  memindahkan atau membalik badan. Peluang mengejar hanya 16% dengan cooldown.
- Koordinat virtual desktop Windows dipakai untuk jalan, kejar, drag, tulang,
  spawn, serta geometry Tk negatif sehingga Dogi dapat masuk monitor lain.
- Walk, chase, dan fetch memakai metadata arah sumber-kiri; sprite dicerminkan
  ketika koordinat bergerak ke kanan sehingga kepala selalu menuju target.
- Animasi bingung memakai urutan `0,1,2,3,2,1`, tiap frame ditahan dua tick;
  transisi siklus tidak lagi melompat dari frame terakhir ke pertama.
- Arah visual walk/chase/fetch dicatat dari delta `x` aktual setiap tick; arah
  target atau kursor tidak dapat membuat sprite tampak berjalan mundur.
- Mengetik memakai empat fase tombol pada setiap empat tingkat merah wajah dan
  mempertahankan state `type` selama input aktif, tanpa frame idle terselip.
- Keyboard mengetik berdiri sebagai prop rendah tersendiri. Scroll memakai prop
  berbeda: laptop tegak, scrollbar bergerak, mouse, dan satu paw aktif.
- Empat behavior baru ikut scheduler kebutuhan/jam, tersedia di menu klik
  kanan, dan tetap dapat diinterupsi input, meeting, drag, atau agent.
- Tujuh pembalikan dengan lintasan minimal 130 px dalam 2,4 detik memicu state
  `dizzy`; gerakan mouse kerja biasa tidak cukup untuk memicunya.
- Gerakan kecil/jitter tidak memicu pusing dan cooldown 30 detik mencegah
  animasi berulang tanpa jeda.
- State drag, fetch, agent thinking, serta meeting alert/watch tidak ditimpa
  oleh gesture pusing.
- Tulang dapat diseret melintasi seluruh virtual desktop. Selama tombol mouse
  ditahan, state `wait_food` menjaga Dogi tetap duduk, menatap tulang, dan
  mengibaskan ekor; saat dilepas state kembali ke `fetch` menuju posisi baru.
- Interaksi teman memakai sesi berpasangan agar kedua jendela tetap sinkron.
  Pose `friend_play` dan `friend_tussle` memiliki siklus manual sendiri;
  `friend_chase` memakai langkah lari dan `friend_cuddle` memakai pose tidur.
- Sprite digendong, mengetik, scroll, meeting, tidur, makan, dan variasi gerak
  lain ikut berpindah ke aset bersih empat frame.

## Verification

- 150 unit test lulus, termasuk tugas, memori, pencarian, backup AES-GCM,
  plugin deklaratif, konteks privat Tanya Dogi, jembatan Codex,
  perekam PCM, transkripsi/notulen rapat,
  detektor gesture, false-positive jitter,
  multi-monitor negatif, glance, kelengkapan 1200 aset tema/arah, alpha PNG, dan
  pemeriksaan keseragaman setiap blok 5 × 5 px.
- PyInstaller dan kedua executable smoke test berhasil.
- `DogiPet.exe` memiliki ProductVersion `1.1.0`.

final result: passed
