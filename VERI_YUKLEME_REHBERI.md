# 📤 Veri Yükleme Rehberi

## 🎯 Amaç

Her gün yeni gelen Excel dosyalarını (yakıt, ağırlık, araç takip) kolayca Supabase veritabanına yüklemek.

---

## 🚀 HIZLI BAŞLANGIÇ

### 1. Uygulamayı Başlatın

```bash
python app.py
```

### 2. Veri Yükleme Sayfasına Gidin

Tarayıcınızda açın:
```
http://localhost:5000/veri-yukleme
```

### 3. Excel Dosyalarını Yükleyin

Sürükle-bırak veya "Dosya Seç" ile:

- ⛽ **Yakıt Verileri**: Günlük yakıt alımları (motorin.xlsx gibi)
- ⚖️ **Ağırlık Verileri**: Taşınan yükler (kantar.xlsx gibi)
- 🚛 **Araç Takip**: GPS ve rota bilgileri (arac_takip.xlsx gibi)

---

## 📊 EXCEL DOSYA FORMATLARI

### ⛽ Yakıt Excel Kolonları

Sistemin tanıdığı kolon isimleri (büyük/küçük harf duyarsız):

| Zorunlu | Kolon İsimleri | Açıklama |
|---------|---------------|----------|
| ✅ | `plaka` | Araç plakası |
| ✅ | `islem_tarihi`, `tarih` | İşlem tarihi |
| ⚪ | `saat` | İşlem saati |
| ✅ | `yakit_miktari`, `miktar` | Yakıt miktarı (litre) |
| ⚪ | `birim_fiyat`, `fiyat` | Litre başı fiyat |
| ⚪ | `satir_tutari`, `tutar`, `toplam` | Toplam tutar |
| ⚪ | `stok_adi`, `yakıt_tipi` | Yakıt tipi (Motorin, Benzin) |
| ⚪ | `km_bilgisi`, `km`, `kilometre` | Araç kilometresi |

**Örnek Excel:**

| plaka | islem_tarihi | yakit_miktari | birim_fiyat | satir_tutari | km_bilgisi |
|-------|-------------|---------------|-------------|--------------|------------|
| 34 ABC 123 | 2024-01-15 | 150.5 | 32.50 | 4891.25 | 45678 |

---

### ⚖️ Ağırlık Excel Kolonları

| Zorunlu | Kolon İsimleri | Açıklama |
|---------|---------------|----------|
| ✅ | `plaka` | Araç plakası |
| ✅ | `tarih` | İşlem tarihi |
| ✅ | `miktar` | Taşınan miktar |
| ✅ | `birim` | Birim (KG, TON, M3, vb.) |
| ⚪ | `net_agirlik`, `net_ağırlık` | Net ağırlık |
| ⚪ | `adres` | Teslimat adresi |
| ⚪ | `islem_noktasi`, `işlem_noktası` | İşlem noktası |
| ⚪ | `cari_adi`, `cari_adı` | Cari adı |

**Örnek Excel:**

| plaka | tarih | miktar | birim | net_agirlik | adres |
|-------|-------|--------|-------|-------------|-------|
| 34 ABC 123 | 2024-01-15 | 15.5 | TON | 15500 | İstanbul |

---

### 🚛 Araç Takip Excel Kolonları

| Zorunlu | Kolon İsimleri | Açıklama |
|---------|---------------|----------|
| ✅ | `plaka` | Araç plakası |
| ✅ | `tarih` | Tarih |
| ⚪ | `sofor_adi`, `şoför_adı` | Şoför adı |
| ⚪ | `arac_gruplari`, `araç_grupları` | Araç grubu |
| ⚪ | `hareket_baslangic_tarihi` | Başlangıç |
| ⚪ | `hareket_bitis_tarihi` | Bitiş |
| ⚪ | `baslangic_adresi` | Başlangıç adresi |
| ⚪ | `bitis_adresi` | Bitiş adresi |
| ⚪ | `toplam_kilometre` | Toplam km |
| ⚪ | `hareket_suresi` | Hareket süresi |
| ⚪ | `rolanti_suresi` | Rölanti süresi |
| ⚪ | `park_suresi` | Park süresi |
| ⚪ | `gunluk_yakit_tuketimi_l` | Günlük yakıt (litre) |

**Örnek Excel:**

| plaka | tarih | toplam_kilometre | gunluk_yakit_tuketimi_l |
|-------|-------|------------------|------------------------|
| 34 ABC 123 | 2024-01-15 | 285 | 48.5 |

---

## ✨ ÖZELLİKLER

### 1. 🎯 Akıllı Kolon Eşleştirme

Sistem Türkçe karakterli kolonları otomatik tanır:
- `İşlem_Tarihi` → `islem_tarihi`
- `Yakıt Miktarı` → `yakit_miktari`
- `Şoför Adı` → `sofor_adi`

### 2. 📈 Incremental Upload

- Mevcut veriler **KOR UNUR**
- Yeni veriler **EKLENIR**
- Duplicate kontrol yapılır

### 3. 🔄 Batch Processing

- 1000'er kayıt halinde yüklenir
- Hızlı ve verimli
- Büyük dosyalar desteklenir

### 4. 📊 Anlık İstatistikler

Yükleme sonrası gösterir:
- ✅ Kaç kayıt eklendi
- 🔄 Kaç duplicate atlandı
- 📊 Toplam kayıt sayısı

---

## 🚨 SORUN GİDERME

### "Dosya yüklenemedi" Hatası

**Sebep:** Excel formatı hatalı

**Çözüm:**
1. Dosyanın `.xlsx` veya `.xls` olduğundan emin olun
2. Excel'i açıp "Farklı Kaydet" → "Excel Workbook (.xlsx)" seçin

### "Zorunlu kolon bulunamadı" Hatası

**Sebep:** Plaka kolonu eksik

**Çözüm:**
1. Excel'de `plaka` kolonu olduğundan emin olun
2. Kolon ismini kontrol edin (büyük/küçük harf önemli değil)

### Yükleme Çok Yavaş

**Sebep:** Dosya çok büyük (>10,000 satır)

**Çözüm:**
1. Dosyayı 5000'er satırlık parçalara bölün
2. Sırayla yükleyin

---

## 💡 İPUÇLARI

### Günlük Rutin

**Her Sabah:**
1. Yeni Excel dosyalarını indir
2. `http://localhost:5000/veri-yukleme` aç
3. Dosyaları sürükle-bırak
4. 2 dakika bekle, tamamlandı! ✅

### Toplu Yükleme

Aynı anda 3 dosyayı da yükleyebilirsiniz:
1. Yakıt Excel'i sürükle → Bekle
2. Ağırlık Excel'i sürükle → Bekle
3. Araç Takip Excel'i sürükle → Bekle

---

## 📞 YARDIM

Sorun yaşarsanız:
1. Tarayıcı konsolu (F12) hatayı kontrol edin
2. Flask terminalini kontrol edin
3. Excel'in ilk 5 satırını örnek olarak gönderin

---

## 🎉 BAŞARILI!

Artık günlük Excel dosyalarınızı **10 saniyede** yükleyebilirsiniz. Komut satırına gerek yok! 🚀
