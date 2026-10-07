# Jam Bandara Nusantara

Dashboard peta 3D bergaya kartun yang menampilkan lokasi bandara Indonesia (kode IATA/ICAO) beserta **waktu lokal** masing-masing, dengan pulau-pulau diwarnai per zona waktu:

| Zona | Offset | Wilayah |
|------|--------|---------|
| **WIB** – Waktu Indonesia Barat | UTC+7 | Sumatera, Jawa, Kalimantan Barat & Tengah |
| **WITA** – Waktu Indonesia Tengah | UTC+8 | Bali, NTB, NTT, Kalimantan Selatan/Timur/Utara, Sulawesi |
| **WIT** – Waktu Indonesia Timur | UTC+9 | Maluku, Maluku Utara, Papua |

## Fitur
- Peta 3D gaya game kartun (Three.js): pulau-pulau timbul berwarna sesuai zona waktu, laut beranimasi, awan melayang.
- Gunung (24 puncak utama, puncak tinggi bersalju, gunung api aktif berasap), sungai besar (Kapuas, Mahakam, Barito, Musi, Bengawan Solo, Mamberamo, Digul, dll.), dan hutan di pulau-pulau besar. Arahkan kursor ke gunung atau sungai untuk melihat namanya.
- 65 bandara dengan label **IATA/ICAO** (mis. `CGK/WIII`) dan jam lokal yang berjalan langsung; label diatur otomatis agar tidak bertumpuk.
- Klik bandara (di peta atau di daftar) untuk terbang ke lokasinya dan melihat jam detik, tanggal, bagian hari, dan selisih dengan jam perangkat Anda.
- **Matahari terbit & terbenam** untuk setiap bandara (dihitung dengan rumus astronomi NOAA/SunCalc): tampil di daftar, kartu detail (beserta hitung mundur), dan di label peta lewat tombol **Label sunset**.
- **Bayangan siang/malam**: sisi Indonesia yang sedang malam diberi bayangan gelap, dengan garis kuning sebagai batas siang/malam (terminator) yang bergerak sesuai posisi matahari sebenarnya. Bisa dimatikan dengan tombol **Siang/malam**.
- Jam besar per zona di bagian atas; klik untuk memfilter dan memusatkan peta ke zona tersebut.
- Pencarian berdasarkan kode IATA, ICAO, nama bandara, kota, atau provinsi.
- Kontrol peta: seret untuk geser, klik kanan / dua jari untuk memutar, scroll / cubit untuk zoom, tombol **Putar** untuk rotasi otomatis.
- Mode terang (siang) dan gelap (malam) mengikuti pengaturan sistem; tampilan responsif untuk ponsel.

## Menjalankan
Cukup buka `index.html` di browser (butuh koneksi internet untuk memuat Three.js dari cdnjs/jsDelivr dan font Google; browser harus mendukung WebGL). Bisa juga di-host lewat GitHub Pages.

## Struktur
- `src/dashboard.html` – template halaman (HTML, CSS, JS, adegan 3D, serta data bandara, gunung, dan sungai).
- `data/provinces.json` – batas provinsi yang sudah disederhanakan dan diberi tag zona waktu.
- `scripts/build.py` – menggabungkan semuanya menjadi `index.html`.
- `scripts/prepare_provinces.py` – membuat `data/provinces.json` dari GeoJSON sumber.

Setelah mengubah template atau data, jalankan:

```bash
python3 scripts/build.py
```

## Sumber data
- Batas provinsi: Peta Dasar BAKOSURTANAL skala 1:250.000 via [superpikar/indonesia-geojson](https://github.com/superpikar/indonesia-geojson). Data ini memakai pembagian provinsi lama (mis. Kepulauan Riau tergabung dengan Riau, Papua belum dimekarkan), tetapi zona waktunya tetap sama.
- Koordinat dan kode IATA/ICAO bandara: dihimpun manual dari data publik bandara (perkiraan, untuk keperluan visualisasi).
- Gunung, sungai, dan hutan: posisi perkiraan, bersifat ilustratif.
