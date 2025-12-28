# 📤 Excel Verilerini Supabase'e Yükleme Rehberi

## ⚡ Hızlı Başlangıç

### Adım 1: Excel Dosyalarını Hazırla
Excel dosyalarınızı proje klasörüne (`project/`) kopyalayın.

**Dosya İsimleri Örnekleri:**
- `1beton satış.xlsx` → Yakıt verileri için
- `1kantar satış.xlsx` → Ağırlık verileri için
- `1motorin.xlsx` → Araç takip verileri için

### Adım 2: Script'i Çalıştır
```bash
python upload_excel_to_supabase.py
```

### Adım 3: Dosya İsimlerini Gir
Script size soracak:
```
⛽ Yakıt Excel dosyası adı: 1beton satış
⚖️  Ağırlık Excel dosyası adı: 1kantar satış
🚛 Araç takip Excel dosyası adı: 1motorin
```

**ÖNEMLİ:** `.xlsx` uzantısını yazmanıza gerek yok! Script otomatik ekler.

---

## 📋 Excel Dosya Formatları

### Yakıt Excel Sütunları
| Sütun Adı | Açıklama | Örnek |
|-----------|----------|-------|
| plaka | Araç plakası | 34 ABC 123 |
| islem_tarihi | İşlem tarihi | 2025-01-15 |
| saat | İşlem saati | 14:30 |
| yakit_miktari | Yakıt miktarı (Litre) | 150.5 |
| birim_fiyat | Birim fiyat | 42.50 |
| satir_tutari | Toplam tutar | 6,396.25 |
| stok_adi | Yakıt türü | Motorin |
| km_bilgisi | Kilometre bilgisi | 125000 |

### Ağırlık Excel Sütunları
| Sütun Adı | Açıklama | Örnek |
|-----------|----------|-------|
| tarih | İşlem tarihi | 2025-01-15 |
| miktar | Miktar | 100 |
| birim | Birim | Ton |
| net_agirlik | Net ağırlık | 98.5 |
| plaka | Araç plakası | 34 ABC 123 |
| adres | Teslimat adresi | İstanbul |
| islem_noktasi | İşlem noktası | Depo 1 |
| cari_adi | Müşteri adı | ABC Şirketi |

### Araç Takip Excel Sütunları
| Sütun Adı | Açıklama | Örnek |
|-----------|----------|-------|
| plaka | Araç plakası | 34 ABC 123 |
| sofor_adi | Sürücü adı | Ahmet Yılmaz |
| arac_gruplari | Araç grubu | Kargo Araçları |
| tarih | Tarih | 2025-01-15 |
| hareket_baslangic_tarihi | Başlangıç | 2025-01-15 08:00 |
| hareket_bitis_tarihi | Bitiş | 2025-01-15 17:30 |
| baslangic_adresi | Başlangıç adresi | İstanbul |
| bitis_adresi | Bitiş adresi | Ankara |
| toplam_kilometre | Toplam KM | 450.5 |
| hareket_suresi | Hareket süresi | 5:30:00 |
| rolanti_suresi | Rölanti süresi | 0:45:00 |
| park_suresi | Park süresi | 3:15:00 |
| gunluk_yakit_tuketimi_l | Günlük yakıt (L) | 85.5 |

---

## 🔍 Sorun Giderme

### ❌ "Dosya bulunamadı" Hatası
**Sebep:** Dosya adı yanlış veya dosya proje klasöründe değil.

**Çözüm:**
1. Dosyanın proje klasöründe olduğunu kontrol edin:
   ```bash
   dir *.xlsx
   ```

2. Dosya adını tam olarak kopyalayıp yapıştırın (uzantı olmadan)

3. Dosya adında Türkçe karakter varsa problem olabilir. Dosya adını İngilizce harflerle değiştirin:
   - `1beton satış.xlsx` → `1beton_satis.xlsx`

### ❌ "0/0 dosya yüklendi" Hatası
**Sebep:** Hiç dosya bulunamadı veya yüklenmedi.

**Çözüm:**
1. Önce script'i çalıştırın, mevcut dosyaları göreceksiniz
2. Listelenen dosya isimlerinden birini seçin
3. Tam olarak kopyalayıp yapıştırın (uzantı olmadan)

### ⚠️ Sütun Adları Uyuşmuyor
**Sebep:** Excel'deki sütun isimleri yukarıdaki tablolarla eşleşmiyor.

**Çözüm:**
1. Excel dosyanızı açın
2. İlk satırdaki başlıkları yukarıdaki tablolara göre düzenleyin
3. Küçük/büyük harf önemli değil (script otomatik düzeltir)
4. Boşluklar önemli değil

---

## 🎯 Test Verileri ile Deneme

Eğer henüz gerçek verileriniz yoksa, test için örnek Excel dosyaları oluşturabilirsiniz:

### Excel'de Hızlı Test Verileri
1. Excel'de yeni bir sayfa aç
2. İlk satıra sütun başlıklarını yaz (yukarıdaki tablolara göre)
3. 2-3 satır örnek veri ekle
4. `test_yakit.xlsx` olarak kaydet
5. Script'i çalıştır ve `test_yakit` yaz

---

## ✅ Başarılı Yükleme Sonrası

Veriler başarıyla yüklendikten sonra:

1. **Flask uygulamasını başlat:**
   ```bash
   python app.py
   ```

2. **Tarayıcıda aç:**
   ```
   http://localhost:5000
   ```

3. **Ana sayfada göreceksin:**
   - Toplam araç sayısı
   - Aktif araç sayısı
   - Toplam yakıt tüketimi
   - Toplam maliyetler

---

## 📞 Yardım

Hala sorun yaşıyorsan:
1. Script çıktısını kopyala
2. Tam hata mesajını paylaş
3. Dosya isimlerini ve konumlarını kontrol et
