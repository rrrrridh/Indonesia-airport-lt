# Jam Bandara Nusantara

Dashboard peta Indonesia yang menampilkan lokasi bandara beserta **waktu lokal** masing-masing, dengan wilayah Indonesia diwarnai per zona waktu:

| Zona | Offset | Wilayah |
|------|--------|---------|
| **WIB** – Waktu Indonesia Barat | UTC+7 | Sumatera, Jawa, Kalimantan Barat & Tengah |
| **WITA** – Waktu Indonesia Tengah | UTC+8 | Bali, NTB, NTT, Kalimantan Selatan/Timur/Utara, Sulawesi |
| **WIT** – Waktu Indonesia Timur | UTC+9 | Maluku, Maluku Utara, Papua |

## Fitur
- Peta provinsi Indonesia diwarnai sesuai zona waktu, plus garis meridian acuan 105°, 120°, 135° BT.
- 65 bandara utama dengan label kode IATA dan jam lokal yang berjalan langsung (label bandara non-hub muncul saat peta di-zoom).
- Klik bandara (di peta atau di daftar) untuk melihat jam detik, tanggal, bagian hari, dan selisih dengan waktu perangkat Anda.
- Jam besar per zona di bagian atas; klik untuk memfilter dan memusatkan peta ke zona tersebut.
- Pencarian berdasarkan kode, nama bandara, kota, atau provinsi.
- Mode terang/gelap mengikuti pengaturan sistem; tampilan responsif untuk ponsel.

## Menjalankan
Cukup buka `index.html` di browser (butuh koneksi internet untuk memuat Leaflet dari cdnjs dan font Google). Bisa juga di-host lewat GitHub Pages.

## Struktur
- `src/dashboard.html` – template halaman (HTML, CSS, JS, dan daftar bandara).
- `src/leaflet.css` – stylesheet Leaflet 1.9.4 (di-inline saat build).
- `data/provinces.json` – batas provinsi yang sudah disederhanakan dan diberi tag zona waktu.
- `scripts/build.py` – menggabungkan semuanya menjadi `index.html`.
- `scripts/prepare_provinces.py` – membuat `data/provinces.json` dari GeoJSON sumber.

Setelah mengubah template atau data, jalankan:

```bash
python3 scripts/build.py
```

## Sumber data
- Batas provinsi: Peta Dasar BAKOSURTANAL skala 1:250.000 via [superpikar/indonesia-geojson](https://github.com/superpikar/indonesia-geojson). Data ini memakai pembagian provinsi lama (mis. Kepulauan Riau tergabung dengan Riau, Papua belum dimekarkan), tetapi zona waktunya tetap sama.
- Koordinat bandara: dihimpun manual dari data publik bandara (perkiraan, untuk keperluan visualisasi).
