# DogiPet Website Design QA

## Acuan dan bukti

- Acuan terpilih: `qa/reference-concept-3.png` (864 x 1821).
- Implementasi desktop: `qa/desktop-hero.png` (864 x 900).
- Implementasi mobile: `qa/mobile-390x844.png` (390 x 844).
- Perbandingan berdampingan: `qa/comparison-hero.png`.
- Halaman yang diuji: `http://localhost:4173/DogiPet/`.

Perbandingan utama memakai crop 864 x 900 dari bagian atas acuan dan viewport
desktop 864 x 900 dari implementasi. Bukti gabungan diperiksa sebagai satu
gambar, bukan dari ingatan. Pengambilan full-page browser menghasilkan stitching
berulang, sehingga tidak dipakai sebagai bukti visual utama; bagian fitur,
privasi, FAQ, dan CTA diperiksa per-region serta melalui DOM.

## Pemeriksaan permukaan

- Desktop 864 x 900: header, headline, ringkasan, jendela desktop, panel unduh,
  tab animasi, grid hitam, tipografi pixel, dan aksen amber tampil utuh.
- Mobile 390 x 844: menu hamburger berfungsi, headline tidak melebar keluar,
  kartu desktop tersusun satu kolom, dan tidak ada horizontal overflow.
- Semua sprite berasal dari aset kanonis aplikasi dan memakai pixel rendering.
- Tombol unduh mengarah ke rolling installer GitHub Release `continuous`.
- Tab Desktop/Mengetik/Rapat/Bermain mengganti pesan dan animasi.
- FAQ dapat dibuka dan ditutup; tautan navigasi menuju section yang benar.
- Tidak ada gambar gagal dimuat, error console, atau warning console.

## Riwayat perbaikan

1. P2: pada lebar 864 px navigasi berubah menjadi menu dan hero menjadi satu
   kolom. Breakpoint diubah dari 920 px ke 760 px.
2. P2: mobile memiliki overflow horizontal 417 px pada viewport 390 px karena
   headline. Ukuran headline mobile dipadatkan; hasil akhir scroll width sama
   dengan client width.
3. P2: label tombol unduh terbungkus di panel sempit. Ukuran/padding label panel
   disesuaikan dan teks dibuat satu baris.

## Hasil akhir

Tidak ada perbedaan P0, P1, atau P2 yang tersisa. Perbedaan kecil pada panjang
halaman dan susunan teks adalah P3 yang disengaja untuk menampung konten produk
DogiPet 2.1 tanpa mengubah bahasa visual acuan.

final result: passed
