# Deforestation Forecast: Kehilangan Tutupan Pohon dan Emisi per Provinsi di Indonesia

Prakiraan kehilangan tutupan pohon (*tree cover loss*) dan emisi karbon bruto untuk 34 provinsi Indonesia, memakai XGBoost dan data Global Forest Watch (GFW). Proyek ini dimulai sebagai tugas kelompok (SDGs 15), lalu saya revisi secara mandiri setelah menemukan kebocoran data (*data leakage*) pada versi pertama.

> **Please Read:** kehilangan tutupan pohon **tidak** sama dengan deforestasi. Angka GFW mencakup semua hilangnya *tree cover*, termasuk pemanenan hutan tanaman dan kebakaran, yang bisa tumbuh kembali. Hasil di sini tidak boleh dibaca sebagai angka deforestasi resmi.

## Ringkasan Hasil

Pada evaluasi yang bebas kebocoran, **XGBoost tidak terbukti lebih akurat daripada tebakan sederhana "sama dengan tahun lalu" (naif)**.

Backtest bergulir 2021-2024 (136 prediksi, satu tahun ke depan, metrik paling andal):

| Model | RMSE (ha) | MAE (ha) | R² | RMSE (log) |
|---|---|---|---|---|
| XGBoost | 15.840 | 8.160 | 0,846 | 0,465 |
| Naif (= tahun lalu) | **15.435** | 8.257 | **0,854** | 0,446 |
| Rata-rata 3 tahun | 16.427 | 8.518 | 0,834 | **0,444** |

Pembagian tunggal berbasis waktu (latih 2006-2020, validasi 2021-2023, uji 2024):

| Set | Model | RMSE (ha) | R² |
|---|---|---|---|
| Validasi 2021-2023 | XGBoost | 15.860 | 0,836 |
| Validasi 2021-2023 | Naif | 16.356 | 0,825 |
| Uji 2024 | XGBoost | 6.151 | 0,980 |
| Uji 2024 | Naif | 12.260 | 0,921 |

Cara membacanya:
- Pada uji 2024, XGBoost jauh lebih baik, tetapi itu hanya **34 titik dalam satu tahun**. Backtest 4 tahun menunjukkan keunggulannya tidak konsisten.
- Pada RMSE skala log, rata-rata 3 tahun sedikit lebih baik daripada XGBoost di backtest dan di uji 2024.
- Hiperparameter dipilih memakai data 2021-2023, sehingga hasil XGBoost pada rentang itu sedikit optimistis.

## Pelajaran: Kebocoran Data pada Versi Pertama

Versi awal melaporkan R² sekitar 0,96. Angka itu tidak dapat dipertanggungjawabkan. Masalah yang ditemukan dan diperbaiki:

| Aspek | Versi awal | Versi revisi |
|---|---|---|
| Fitur perubahan (`pct_change`) | Memuat nilai target tahun berjalan | Semua fitur memakai data sampai tahun *t-1*; ada uji otomatis di notebook |
| Rata-rata per provinsi dan imputasi median | Dihitung dari seluruh data, termasuk masa depan | Dihapus |
| `year`, tren, sin/cos | Dipakai | Dihapus (model pohon tidak dapat mengekstrapolasi tahun) |
| Emisi | Rumus buatan sendiri (2,67 kali angka GFW) | Kolom emisi bruto resmi GFW |
| Prakiraan rekursif | Semua lag diisi nilai yang sama | Semua fitur dihitung ulang di setiap langkah |
| Evaluasi | Acak, tanpa pembanding | Berbasis waktu, dengan baseline naif dan backtest bergulir |

Dampak pada emisi 2001-2024: total GFW adalah 23,2 miliar Mg CO₂e, sedangkan rumus lama menghasilkan 62,1 miliar Mg CO₂e.

## Data

- **Sumber:** Global Forest Watch, berkas `IDN.xlsx` (sheet *Subnational 1 tree cover loss* dan *Subnational 1 carbon data*), ambang tutupan 30%, 34 provinsi, tahun 2001-2024.
- **Emisi:** kolom `gfw_forest_carbon_gross_emissions_{tahun}__Mg_CO2e`. Metodologinya mengacu pada sitasi di sheet *Read_Me* berkas GFW:
  - Harris et al. (2021), *Nature Climate Change* 11: 234-240.
  - Gibbs et al. (2025), *Earth System Science Data* 17(3): 1217-1243.
- **Lisensi data:** periksa ketentuan lisensi dan atribusi di situs Global Forest Watch sebelum menggunakan ulang data ini. <!-- TODO: isi pernyataan lisensi setelah diverifikasi -->

## Metode

- **Target:** `loss_ha` per provinsi per tahun (transformasi log1p saat pelatihan).
- **Fitur (semua dari tahun sebelumnya):** `lag_1`, `lag_2`, `lag_3`, `lag_5`, `roll_mean_3`, `roll_mean_5`, `roll_std_3`, `roll_std_5`, `diff_1`, `diff_3`, `log_extent`.
- **Model:** XGBoost dengan 40 percobaan Optuna (TPE) dan *early stopping*; benih acak 42.
- **Evaluasi:** pembagian berbasis waktu dan backtest bergulir, dibandingkan dengan baseline naif dan rata-rata 3 tahun.
- **Prakiraan 2025-2030:** rekursif, dengan seluruh fitur dihitung ulang di setiap langkah.
- **Emisi prakiraan:** `loss_ha` dikali faktor emisi per provinsi (rata-rata 2020-2024). Faktor nasional 614,1 Mg CO₂e/ha dipakai bila faktor provinsi tidak terdefinisi.

Prakiraan nasional 2025-2030 menurun halus dari sekitar 1,06 juta ha ke 0,96 juta ha per tahun. Data historis berfluktuasi antara sekitar 0,5 dan 2,4 juta ha. Garis yang mulus ini adalah perilaku model yang cenderung kembali ke rata-rata, **bukan** bukti bahwa kehilangan tutupan pohon akan menurun.

## Struktur Repositori

```
.
├── .github/workflows/update_forecast.yml   # menjalankan forecast_update.py
├── data/
│   ├── deforestation_historical_forecast_full.csv   # historis + prakiraan (kolom source)
│   ├── history_ready.csv                            # riwayat bersih untuk skrip
│   ├── evaluation_split.csv                         # metrik pembagian waktu
│   └── evaluation_backtest.csv                      # metrik backtest bergulir
├── model/
│   ├── xgb_model.json
│   └── metadata.json                                # fitur, parameter, faktor emisi
├── notebooks/deforestation_revised.ipynb            # analisis lengkap
├── forecast_update.py
└── requirements.txt
```

Kolom `deforestation_historical_forecast_full.csv`: `subnational1`, `year`, `loss_ha`, `loss_rate_%`, `emission_CO2e`, `source` (`historical` atau `forecast`).

## Cara Menjalankan

```bash
pip install -r requirements.txt
python forecast_update.py
```

Skrip membaca `data/history_ready.csv`, `model/xgb_model.json`, dan `model/metadata.json`, lalu menulis ulang `data/deforestation_historical_forecast_full.csv`. Untuk melatih ulang dari awal, jalankan `notebooks/deforestation_revised.ipynb` (diuji di Google Colab dengan xgboost 3.4.1, optuna 5.0.0, scikit-learn 1.6.1, pandas 2.2.3).

**Catatan GitHub Actions:** skrip tidak mengunduh data GFW baru. Selama `history_ready.csv` tidak diperbarui, hasil prakiraan tidak berubah dan tidak ada commit otomatis. GFW merilis data setahun sekali, jadi pembaruan perlu dimulai dengan memperbarui data riwayat secara manual.

## Dashboard

Dashboard Looker Studio: [https://datastudio.google.com/reporting/7d116743-5507-4a38-81ac-94c38c66238f/page/nkUdF/edit] 
> Sheet sumber data diperbarui manual dari CSV di folder data/

Keterbatasan yang perlu diperhatikan saat membaca dashboard:
- Pastikan kartu KPI difilter ke `source = historical`. Total yang mencampur data historis dan prakiraan akan menyesatkan.
- Emisi dalam Mg CO₂e (setara ton CO₂e); pastikan satuan tertulis di setiap grafik.
- Kehilangan tutupan pohon dan emisi sangat berkorelasi karena emisi dihitung dari kehilangan tutupan pohon, sehingga korelasi itu bukan temuan.
- Kerapatan karbon harus diagregasi dengan rata-rata, bukan jumlah.

## Keterbatasan

1. Kehilangan tutupan pohon bukan deforestasi (lihat catatan di atas).
2. XGBoost belum terbukti mengungguli baseline naif pada backtest bergulir.
3. Evaluasi hanya mencakup 4 tahun uji, sehingga kesimpulan sangat sensitif terhadap tahun-tahun tertentu.
4. Prakiraan tidak memiliki interval ketidakpastian.
5. Faktor emisi diasumsikan konstan pada rata-rata 2020-2024, jadi emisi prakiraan bukan prakiraan emisi yang independen.
6. Pilihan lag (1, 2, 3, 5) dan horizon 6 tahun belum diuji terhadap alternatif.
7. Model tidak memakai variabel penyebab (kebijakan, harga komoditas, iklim, kebakaran).

## Kontributor

Proyek kelompok (Kelompok 6, SDGs 15). Revisi metodologi, perbaikan kebocoran data, dan otomatisasi oleh [@zrasyafira](https://github.com/zrasyafira).

## Lisensi

<!-- TODO: pilih lisensi kode (misalnya MIT) -->
