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
- **METAR per 30 menit**: laporan cuaca bandara (METAR/SPECI) dari NOAA Aviation Weather Center (laporan stasiun BMKG), diterjemahkan ke bahasa Indonesia (angin, jarak pandang, cuaca, awan, suhu, QNH, tren) beserta kategori penerbangan VFR/MVFR/IFR/LIFR. Tampil di kartu bandara, daftar, titik warna di label peta, dan awan hujan/petir 3D di atas bandara yang sedang hujan.
- Jam besar per zona di bagian atas; klik untuk memfilter dan memusatkan peta ke zona tersebut.
- Pencarian berdasarkan kode IATA, ICAO, nama bandara, kota, atau provinsi.
- Kontrol peta: seret untuk geser, klik kanan / dua jari untuk memutar, scroll / cubit untuk zoom, tombol **Putar** untuk rotasi otomatis.
- Mode terang (siang) dan gelap (malam) mengikuti pengaturan sistem; tampilan responsif untuk ponsel.

## Menjalankan
Cukup buka `index.html` di browser (butuh koneksi internet untuk memuat Three.js dari cdnjs/jsDelivr dan font Google; browser harus mendukung WebGL). Bisa juga di-host lewat GitHub Pages.

## METAR otomatis (GitHub Actions + GitHub Pages)
Workflow `.github/workflows/metar.yml` berjalan **setiap 30 menit**:
1. `scripts/fetch_metar.py` mengambil METAR terbaru ke-65 bandara. Sumber utamanya adalah portal penerbangan BMKG (`web-aviation.bmkg.go.id`), dengan cadangan NOAA Aviation Weather Center (`aviationweather.gov`) yang menyebarkan laporan stasiun BMKG yang sama. **Saat ini portal BMKG dilindungi tantangan anti-bot Cloudflare**, sehingga skrip otomatis tidak bisa mengaksesnya dan seluruh data berasal dari NOAA (sekitar 27 dari 65 bandara punya laporan dalam 3 jam terakhir). Skrip tidak mencoba melewati tantangan itu. Untuk data langsung dari BMKG, minta akses resmi (API atau langganan data) ke BMKG. Sumber tiap stasiun dicatat di `data/metar.json`.
2. Hasilnya (`data/metar.json`) dipublikasikan bersama `index.html` ke GitHub Pages. Halaman memeriksa file baru setiap 5 menit.

Cara mengaktifkan:
- Gabungkan branch ini ke `main` (jadwal GitHub Actions hanya berjalan di branch default).
- Buka **Settings → Pages → Source** dan pilih **GitHub Actions**. (GitHub Pages untuk repo privat butuh paket berbayar.)
- Jalankan sekali lewat **Actions → METAR update & deploy → Run workflow**, lalu cek log langkah *Fetch METAR*. Log menunjukkan berapa stasiun yang didapat dari BMKG dan dari NOAA.
- Jika BMKG kelak memberi akses resmi (mis. alamat API atau kunci), alamatnya bisa diatur lewat **Settings → Secrets and variables → Actions → Variables**: `BMKG_METAR_URL`, `BMKG_METAR_FIELD`, `BMKG_METAR_METHOD` (lihat keterangan di `scripts/fetch_metar.py`).

Menjalankan secara lokal: `python3 scripts/fetch_metar.py data/metar.json`, lalu buka lewat server lokal (`python3 -m http.server`), karena browser memblokir `fetch` dari `file://`.

Data METAR di dashboard hanya untuk informasi, bukan pengganti briefing meteorologi penerbangan resmi.

## Struktur
- `src/dashboard.html` – template halaman (HTML, CSS, JS, adegan 3D, serta data bandara, gunung, dan sungai).
- `data/provinces.json` – batas provinsi yang sudah disederhanakan dan diberi tag zona waktu.
- `scripts/build.py` – menggabungkan semuanya menjadi `index.html`.
- `scripts/fetch_metar.py` – mengambil METAR (BMKG, cadangan NOAA AWC) ke `data/metar.json`.
- `.github/workflows/metar.yml` – jadwal 30 menit: ambil METAR, build, deploy ke GitHub Pages.
- `scripts/prepare_provinces.py` – membuat `data/provinces.json` dari GeoJSON sumber.

Setelah mengubah template atau data, jalankan:

```bash
python3 scripts/build.py
```

## Sumber data
- Batas provinsi: Peta Dasar BAKOSURTANAL skala 1:250.000 via [superpikar/indonesia-geojson](https://github.com/superpikar/indonesia-geojson). Data ini memakai pembagian provinsi lama (mis. Kepulauan Riau tergabung dengan Riau, Papua belum dimekarkan), tetapi zona waktunya tetap sama.
- Koordinat dan kode IATA/ICAO bandara: dihimpun manual dari data publik bandara (perkiraan, untuk keperluan visualisasi).
- Gunung, sungai, dan hutan: posisi perkiraan, bersifat ilustratif.
