# Memasang API resmi BMKG untuk METAR

Catatan ini untuk saat Anda mendapat akses resmi ke data METAR dari BMKG (API, URL langganan data, atau sejenisnya).
Selama belum ada, dashboard memakai data NOAA Aviation Weather Center, dan tidak ada yang perlu diubah.

## 1. Cek dulu dokumentasi dari BMKG

Sebelum mengisi apa pun, cari empat hal ini di dokumentasi atau email dari BMKG:

| Pertanyaan | Kenapa penting |
|---|---|
| **Alamat (URL) endpoint METAR** | Diisi ke `BMKG_METAR_URL`. |
| **Apakah butuh kunci / token?** Kalau ya, dikirim lewat header atau parameter URL? | Kunci **tidak boleh** ditaruh di variables (lihat bagian 4). |
| **Cara memilih bandara**: semua sekaligus, satu per permintaan, atau daftar kode ICAO? Pemisahnya spasi atau koma? | Skrip mengirim ke-65 kode ICAO **dipisah spasi** dalam satu parameter. |
| **Isi responsnya**: apakah memuat teks METAR mentah seperti `METAR WIII 071030Z 05008KT 9000 ... Q1009 NOSIG=`? | Skrip membaca teks METAR mentah. Kalau API hanya memberi data yang sudah diurai (suhu, angin, dll. dalam kolom terpisah), skrip perlu diubah. |

## 2. Variables yang tersedia

Diatur di GitHub: **Settings → Secrets and variables → Actions → tab Variables → New repository variable**.

| Variable | Isi | Wajib? |
|---|---|---|
| `BMKG_METAR_URL` | Alamat endpoint METAR dari BMKG. | Ya |
| `BMKG_METAR_FIELD` | Nama parameter untuk daftar kode ICAO, misalnya `icao` atau `stations`. | Hanya jika endpoint perlu daftar bandara |
| `BMKG_METAR_METHOD` | `GET` atau `POST`. Kalau kosong, dipakai `POST`. | Hanya jika endpoint perlu daftar bandara |

Cara skrip memakainya (`scripts/fetch_metar.py`):

1. Skrip membuka `BMKG_METAR_URL` apa adanya dengan GET. Kalau responsnya sudah berisi METAR bandara-bandara di dashboard, data itu langsung dipakai. Pada langkah ini `BMKG_METAR_FIELD` dan `BMKG_METAR_METHOD` tidak dipakai.
2. Kalau belum, skrip mengirim ke-65 kode ICAO, dipisah spasi, lewat parameter `BMKG_METAR_FIELD` dengan metode `BMKG_METAR_METHOD`.
   - `GET` menghasilkan `…?<FIELD>=WITT WIMM WIMN …`.
   - `POST` mengirim form biasa (`application/x-www-form-urlencoded`).
3. Bandara yang tidak didapat dari BMKG tetap diisi dari NOAA, jadi dashboard tidak pernah kosong karena BMKG.

Format respons boleh apa saja (teks, HTML, JSON, XML), selama di dalamnya ada teks METAR/SPECI mentah. Laporan yang lebih tua dari 6 jam diabaikan.

## 3. Contoh pengisian

**A. Endpoint yang langsung memberi semua METAR Indonesia** (paling mudah)

```
BMKG_METAR_URL    = https://<alamat-dari-BMKG>/metar/latest
BMKG_METAR_FIELD  = (kosongkan)
BMKG_METAR_METHOD = (kosongkan)
```

**B. Endpoint yang meminta daftar bandara lewat parameter URL**

```
BMKG_METAR_URL    = https://<alamat-dari-BMKG>/metar
BMKG_METAR_FIELD  = icao        ← sesuaikan dengan nama di dokumentasi BMKG
BMKG_METAR_METHOD = GET
```

**C. Endpoint berupa form yang dikirim dengan POST**

```
BMKG_METAR_URL    = https://<alamat-dari-BMKG>/metar_speci.php
BMKG_METAR_FIELD  = <nama isian formulir>
BMKG_METAR_METHOD = POST
```

## 4. Kunci API / token: jangan taruh di variables

Variables bisa dibaca siapa pun yang punya akses ke repo, dan `BMKG_METAR_URL` dicetak di log Actions. Jadi:

- **Jangan** menyisipkan kunci di URL, misalnya `...?apikey=...`, lewat variables.
- Simpan kunci sebagai **Secret**: **Settings → Secrets and variables → Actions → tab Secrets → New repository secret**, misalnya dengan nama `BMKG_API_KEY`. GitHub otomatis menyamarkan secret di log.
- Skrip saat ini **belum** membaca secret apa pun. Perlu tambahan kecil di `scripts/fetch_metar.py` dan `.github/workflows/metar.yml` sesuai cara BMKG meminta kunci (header seperti `Authorization: Bearer …` atau `X-API-Key: …`, atau parameter URL).

## 5. Kasus yang perlu perubahan kode

Variables saja tidak cukup jika endpoint BMKG:

- butuh kunci API atau token (bagian 4);
- meminta kode bandara dipisah **koma**, atau hanya **satu bandara per permintaan**;
- meminta isi permintaan berformat JSON;
- hanya mengembalikan data yang sudah diurai, tanpa teks METAR mentah.

Untuk kasus-kasus ini, siapkan dokumentasi API dari BMKG (alamat, contoh permintaan, contoh respons), lalu sesuaikan skripnya. Jangan cantumkan kunci aslinya di mana pun.

## 6. Menguji setelah mengisi variables

1. Buka **Actions → METAR update & deploy → Run workflow** (branch `main`).
2. Setelah selesai, buka job **fetch**, langkah **Fetch METAR**. Lihat barisnya:
   - `BMKG GET …: HTTP 200 …` artinya endpoint terjangkau.
   - `BMKG … -> N stations` artinya N bandara didapat dari BMKG.
   - `AWC: N stations` artinya bandara sisanya diisi dari NOAA.
   - `… 27/65 stations written …` adalah jumlah total bandara yang punya METAR.
3. Di dashboard, kartu bandara menampilkan **Sumber: BMKG** untuk data dari BMKG.

Kalau log menunjukkan `HTTP 401`/`403`, biasanya kuncinya belum dikirim atau salah. `HTTP 404` biasanya berarti URL salah. `0 stations` dengan `HTTP 200` berarti format responsnya tidak memuat teks METAR mentah, atau nama parameternya salah.

## 7. Mengembalikan ke NOAA saja

Hapus ketiga variables (`BMKG_METAR_URL`, `BMKG_METAR_FIELD`, `BMKG_METAR_METHOD`). Skrip kembali ke alamat portal BMKG bawaan, yang saat ini terhalang Cloudflare, sehingga semua data datang dari NOAA seperti sebelumnya.
