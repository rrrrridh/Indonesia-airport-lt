# METAR langsung dari dashboard (tombol **Perbarui**)

Tombol **Perbarui** di atas daftar bandara mengambil METAR terbaru saat itu juga. Setelah aktif,
dashboard juga memperbaruinya sendiri setiap 10 menit selama halaman terbuka. Cara ini tidak bergantung
pada jadwal GitHub Actions.

## Kenapa perlu perantara (Cloudflare Worker)

Browser hanya boleh membaca data dari situs lain jika situs itu mengizinkannya lewat header **CORS**.

- **NOAA Aviation Weather Center** (`aviationweather.gov`) tidak mengirim header itu. Ini sudah diuji
  pada 16 Okt 2026. Akibatnya dashboard di GitHub Pages tidak bisa memanggil NOAA langsung.
- **Portal BMKG** dilindungi tantangan anti-bot Cloudflare, jadi juga tidak bisa dipakai.

Karena itu dipakai sebuah **Cloudflare Worker**, yaitu skrip kecil gratis di server Cloudflare
(kodenya ada di [`worker/metar-proxy.js`](../worker/metar-proxy.js)). Worker ini:

- menerima `GET /?ids=WIII,WADD,…` dari dashboard, hanya untuk kode ICAO Indonesia (`W…`, maksimal 200);
- mengambil METAR mentah dari NOAA, 40 stasiun per permintaan;
- mengembalikannya dengan izin CORS **hanya** untuk `https://rrrrridh.github.io` (dan `localhost:8000` untuk uji lokal);
- menyimpan hasil di cache selama 2 menit, sehingga klik berulang dari banyak pengunjung tidak membebani NOAA;
- tidak menyimpan rahasia atau token apa pun.

Paket gratis Cloudflare Workers memberi 100.000 permintaan per hari, jauh di atas kebutuhan dashboard ini.

Tanpa Worker, tombol **Perbarui** tetap ada, tetapi hanya memuat ulang `data/metar.json`, yaitu data terakhir
yang dibuat saat situs di-deploy.

---

## 1. Buat Worker (lewat dashboard Cloudflare, tanpa instal apa pun)

1. Daftar atau masuk di <https://dash.cloudflare.com>. Akun gratis sudah cukup.
2. Menu kiri **Compute (Workers)** → **Workers & Pages** → **Create** → **Create Worker**. Di beberapa
   tampilan, tombolnya bernama **Start with Hello World**.
3. Beri nama, misalnya `metar-proxy`, lalu klik **Deploy**.
4. Klik **Edit code**. Hapus seluruh isi `worker.js`, lalu tempel **seluruh** isi
   [`worker/metar-proxy.js`](../worker/metar-proxy.js) dari repo ini.
5. Klik **Deploy**.
6. Catat alamat Worker, misalnya `https://metar-proxy.<nama-akun>.workers.dev`.

Kalau dashboard nanti dipasang di domain lain, tambahkan domain itu ke daftar `ALLOWED_ORIGINS`
di bagian atas kode Worker, lalu deploy ulang.

## 2. Uji Worker

Buka alamat ini di browser (ganti alamatnya):

```
https://metar-proxy.<nama-akun>.workers.dev/?ids=WIII,WADD,WARR
```

Hasil yang benar berupa beberapa baris teks, misalnya `METAR WIII 160830Z 05008KT 9000 …`.

- **`Pass ids=…`** (HTTP 400): parameter `ids` kosong atau berisi kode yang bukan ICAO Indonesia.
- **`NOAA AWC answered HTTP …`** (HTTP 502): NOAA sedang bermasalah. Coba lagi beberapa menit kemudian.

## 3. Sambungkan ke dashboard

Isi alamat Worker di `src/dashboard.html`, pada baris:

```js
const METAR_LIVE_URL = "";   // e.g. "https://metar-proxy.<akun>.workers.dev"
```

Setelah diisi, bangun ulang halaman dengan `python3 scripts/build.py` lalu commit, atau minta Claude yang
mengerjakannya: cukup kirim alamat Worker-nya. Alamat ini bukan rahasia, jadi aman ditaruh di repo.

Setelah di-deploy, status di atas daftar bandara akan berbunyi
*METAR 27/133 bandara · 16:05 WIB · langsung dari NOAA*.

- Kalau Worker tidak bisa dihubungi, dashboard otomatis memakai data terakhir dari server dan menampilkan tanda ⚠.
- Arahkan kursor ke status itu untuk melihat keterangannya.

## Tentang GitHub Actions

Dengan Worker aktif, data di dashboard tidak lagi bergantung pada jadwal GitHub Actions.

- Workflow **METAR update & deploy** tetap dibutuhkan untuk menerbitkan situs ke GitHub Pages setiap kali
  ada perubahan di `main`. Workflow itu juga membuat `data/metar.json` sebagai cadangan.
- Jadwal 30 menitnya boleh dimatikan, dengan menghapus blok `schedule:` di `.github/workflows/metar.yml`.
  Sebaiknya lakukan ini setelah Worker terbukti berjalan.
