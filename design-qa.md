# Design QA — DogiPet 0.4.0

**Source visual truth**

- `I:/apps anjing/source-captures/comnyang-desktop.png` — referensi bahasa
  visual hitam, putih, kuning, tipografi pixel, border tipis, dan kartu.
- `new_frames_preview.png` — sprite Dogi asli dari ZIP pengguna.

**Implementation evidence**

- `qa/control-center-reactions-v040.png` — halaman Reaksi dari packaged EXE.
- `qa/reactions-v040.png` — scroll atas/bawah, meeting alert, dan meeting watch.
- `qa/control-center-v030.png` — struktur Beranda yang tetap dipertahankan.

**Viewport and state**

- Windows 11, display scaling 125%, 948 × 780 physical px.
- Halaman Reaksi, semua toggle aktif, tidak ada meeting aktif.

**Full-view comparison evidence**

Halaman baru mempertahankan token visual Control Center: latar `#090909`, panel
`#151515`, border `#383838`, teks hangat, aksen `#f2cf45`, sidebar konsisten,
dan tombol state besar yang mudah dipahami. Semua tujuh halaman muat dalam
content 680 × 620 px tanpa clipping.

**Focused region comparison evidence**

`qa/reactions-v040.png` memperlihatkan indikator scroll berpindah sesuai arah,
gelombang gonggongan pada dua frame meeting alert, serta pose meeting watch.
Semua frame tetap memakai grid 16 × 12 tanpa smoothing.

## Findings

- Tidak ada temuan P0, P1, atau P2.
- [P3] Deteksi meeting memakai heuristik nama executable dan judul jendela.
  Aplikasi rapat yang belum ada dalam daftar dapat ditambahkan pada iterasi
  berikutnya tanpa mengubah model privasi.

## Required fidelity surfaces

- Fonts and typography: Consolas bold, hierarchy dan wrapping terbaca pada
  scaling 125%.
- Spacing and layout rhythm: header 76 px, sidebar 196 px, content 680 × 620 px,
  gap kartu 12 px.
- Colors and visual tokens: konsisten dengan Control Center sebelumnya dan
  referensi visual.
- Image quality and asset fidelity: animasi memakai sprite Dogi asli dan marker
  pixel; tidak ada placeholder atau aset generik.
- Copy and content: Bahasa Indonesia, istilah meeting populer tetap mudah
  dikenali, dan batas privasi dijelaskan langsung di UI.

## Interactions verified

- Scroll global mengaktifkan state `scroll_up` atau `scroll_down`, lalu kembali
  ke idle/type setelah aktivitas berhenti.
- Meeting baru mengarahkan Dogi ke pusat jendela, mengaktifkan `meeting_alert`,
  dan menggonggong sekali bila toggle suara aktif.
- Meeting yang berlanjut memunculkan variasi `meeting_watch` tanpa gonggongan
  berulang; state hilang setelah jendela rapat tidak terlihat.
- Toggle scroll, meeting, dan gonggongan tersimpan di konfigurasi lokal.
- Deteksi hanya membaca app, judul, dan posisi jendela; tidak mengakses kamera,
  mikrofon, peserta, atau isi meeting.

## Verification

- 36 unit test lulus, termasuk matcher Zoom/Teams/Meet/Webex/Slack/Discord,
  false-positive cases, frame grid, arah scroll, dan reaksi meeting.
- Pencarian jendela meeting Windows berjalan tanpa error pada mesin target.
- Source smoke test, page-fit test, dan packaged reaction-page smoke lulus.
- Packaged executable/installer memiliki metadata versi `0.4.0`.

final result: passed
