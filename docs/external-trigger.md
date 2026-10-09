# Pemicu eksternal untuk update METAR tiap 30 menit

Jadwal bawaan GitHub (`schedule` di `.github/workflows/metar.yml`) ternyata jarang berjalan untuk repo ini.
Dalam 24 jam pertama hanya 4 dari sekitar 48 jadwal yang berjalan, masing-masing terlambat ±13 menit.
Panduan ini memasang **pemicu dari luar GitHub**: layanan cron gratis (cron-job.org) memanggil API GitHub
setiap 30 menit untuk menjalankan workflow **METAR update & deploy**.

Tidak ada kode yang perlu diubah. Workflow sudah menerima pemicu manual (`workflow_dispatch`),
dan jadwal bawaan GitHub tetap aktif sebagai cadangan.

Ringkasan langkah:
1. Buat token GitHub dengan izin seminimal mungkin.
2. Uji token dengan satu perintah `curl`.
3. Pasang jadwal di cron-job.org.
4. Pastikan run muncul di tab Actions.

---

## 1. Buat fine-grained token (izin minimum)

1. Buka GitHub → foto profil (kanan atas) → **Settings** → **Developer settings** (paling bawah di menu kiri)
   → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Isi:
   - **Token name**: misalnya `cron-job.org METAR Indonesia-airport-lt`.
   - **Expiration**: pilih tanggal, misalnya 1 tahun. Catat tanggalnya, karena pemicu akan berhenti saat token kedaluwarsa (lihat bagian 6).
   - **Resource owner**: `rrrrridh`.
   - **Repository access**: **Only select repositories** → pilih **`rrrrridh/Indonesia-airport-lt`** saja.
3. Di **Permissions → Repository permissions**, ubah **hanya** baris ini:
   - **Actions** → **Read and write**.

   *Metadata: Read-only* akan ikut terpilih otomatis dan memang wajib. Biarkan semua izin lain di **No access**.
4. Klik **Generate token**, lalu salin tokennya (diawali `github_pat_…`).
   Token hanya ditampilkan sekali. **Jangan** simpan token ini di repo, di issue, atau di chat, termasuk ke Claude.

> **Apa yang bisa dilakukan token ini?** Hanya tindakan *Actions* di repo ini: menjalankan, menjalankan ulang,
> atau membatalkan workflow, mengaktifkan/menonaktifkan workflow, serta melihat dan menghapus log run dan artefak. Token ini **tidak** bisa membaca atau mengubah
> kode, mengubah file workflow, membuat rilis, atau menyentuh repo lain. Kalau bocor, dampak terburuknya
> terbatas pada run Actions di repo ini, dan token bisa langsung dicabut (bagian 6).

---

## 2. Uji token dengan `curl`

Jalankan di terminal komputer Anda. Ganti `TOKEN_ANDA` dengan token tadi:

```bash
curl -i -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer TOKEN_ANDA" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/rrrrridh/Indonesia-airport-lt/actions/workflows/metar.yml/dispatches \
  -d '{"ref":"main"}'
```

- **`HTTP/2 204`** berarti berhasil. Dalam beberapa detik, run baru muncul di tab **Actions** dengan keterangan *Manually run by rrrrridh*.
- **`401`** berarti token salah atau sudah kedaluwarsa.
- **`403`** berarti izin *Actions: Read and write* belum diberikan, atau repo tidak dipilih saat membuat token.
- **`404`** berarti salah ketik pada nama repo atau nama file workflow, atau token tidak punya akses ke repo ini.
- **`422`** berarti `ref` salah. Pastikan isinya `"main"`.

Di Windows (PowerShell), ganti `curl` dengan `curl.exe`. Kalau tanda kutip bermasalah, isi body bisa ditulis sebagai `-d "{\"ref\":\"main\"}"`.

---

## 3. Pasang jadwal di cron-job.org

1. Daftar atau masuk di <https://cron-job.org>. Layanannya gratis.
2. **Dashboard** → **Create cronjob**.
3. Tab **Common**:
   - **Title**: `METAR Indonesia-airport-lt`
   - **URL**: `https://api.github.com/repos/rrrrridh/Indonesia-airport-lt/actions/workflows/metar.yml/dispatches`
   - **Execution schedule**: pilih **Custom**, lalu centang **Every hour** dan menit **7** dan **37**.
     Jadi pemicu berjalan setiap 30 menit di menit :07 dan :37. Menit ini sengaja tidak sama dengan jadwal
     GitHub (:13/:43) dan bukan menit sibuk :00/:30. **Time zone** boleh apa saja, karena pengaturannya per menit.
4. Tab **Advanced**:
   - **Request method**: `POST`
   - **Headers**: tambahkan tiga baris berikut.
     | Key | Value |
     |---|---|
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer TOKEN_ANDA` |
     | `X-GitHub-Api-Version` | `2022-11-28` |
   - **Request body**: `{"ref":"main"}`
   - **Treat redirects with HTTP 3xx status code as success**: tidak perlu dicentang.
5. Tab **Notifications** (disarankan): aktifkan **notify on failure**, supaya Anda dapat email kalau
   panggilan gagal, misalnya karena token kedaluwarsa.
6. Klik **Create**. Untuk mencoba sekarang, buka cronjob tersebut lalu klik **Test run**. Hasilnya harus `204 No Content`.

---

## 4. Memastikan berjalan

- Tab **Actions** → workflow **METAR update & deploy**: setiap ~30 menit muncul run baru dengan keterangan
  *Manually run by rrrrridh*. Event-nya `workflow_dispatch`, karena run dipicu lewat token Anda.
- Kartu bandara dan status di atas daftar bandara di dashboard menunjukkan *diperbarui HH:MM WIB*.
  Waktu itu seharusnya tidak pernah lebih dari ±35 menit di belakang jam sekarang.
- Di cron-job.org, menu **History** pada cronjob itu menunjukkan status setiap panggilan.

Bila pemicu eksternal dan jadwal GitHub kebetulan berjalan bersamaan, workflow otomatis membatalkan run yang
lebih lama (`concurrency` dengan `cancel-in-progress`), jadi tidak ada deploy ganda.

Biaya: repo ini publik, jadi menit GitHub Actions gratis. Satu run makan waktu sekitar 30–45 detik.

---

## 5. Opsional: matikan jadwal GitHub

Setelah pemicu eksternal terbukti stabil beberapa hari, jadwal GitHub boleh dibiarkan sebagai cadangan.
Kalau ingin dimatikan, hapus blok `schedule:` di `.github/workflows/metar.yml` lewat PR.
Saran saya tetap dibiarkan, karena tidak ada ruginya.

---

## 6. Perawatan token

- **Sebelum kedaluwarsa**: buat token baru dengan langkah yang sama, ganti nilai header `Authorization`
  di cron-job.org, jalankan **Test run**, lalu hapus token lama.
- **Mencabut** (misalnya bila token bocor atau pemicu tidak dipakai lagi): GitHub → Settings → Developer settings →
  Personal access tokens → Fine-grained tokens → pilih token → **Delete**. Setelah itu nonaktifkan atau hapus cronjob
  di cron-job.org. Workflow tetap bisa dijalankan manual dan lewat jadwal GitHub.
- Bila notifikasi gagal dari cron-job.org mulai muncul, cek dulu tanggal kedaluwarsa token.
