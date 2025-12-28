# 🚛 Kargo Yakıt Analiz Sistemi

Modern, web tabanlı kargo yakıt takip ve analiz sistemi. Supabase PostgreSQL + Flask.

---

## ✨ YENİ ÖZELLİKLER

### 📤 Web'den Excel Yükleme
- ✅ Sürükle-bırak desteği
- ✅ Gerçek zamanlı progress bar
- ✅ Otomatik duplicate kontrolü
- ✅ Günlük veri aktarımı kolaylaştı!

**Artık komut satırına gerek yok!** Web arayüzünden her şeyi yapın.

---

## 🚀 HIZLI BAŞLANGIÇ

### 1. Projeyi Klonlayın
```bash
git clone <repo-url>
cd project
```

### 2. Gereksinimleri Yükleyin
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
`.env` dosyası zaten hazır:
```
VITE_SUPABASE_URL=https://qlwycqwquapwwgfysscy.supabase.co
VITE_SUPABASE_ANON_KEY=...
```

### 4. Uygulamayı Başlatın
```bash
python app.py
```

### 5. Veri Yükleyin
Tarayıcıda açın:
```
http://localhost:5000/veri-yukleme
```

Excel dosyalarınızı sürükle-bırak yapın. Hepsi bu! 🎉

---

## 📁 PROJE YAPISI

```
project/
├── app.py                      # Ana Flask uygulaması
├── database.py                 # Supabase işlemleri
├── ai_model.py                 # AI tahmin modelleri
├── model_analyzer.py           # Veri analizi
├── requirements.txt            # Python gereksinimleri
├── render.yaml                 # Render.com config
├── templates/
│   ├── index.html              # Ana sayfa
│   ├── veri_yukleme.html       # ⭐ YENİ: Excel yükleme sayfası
│   ├── result.html             # Analiz sonuçları
│   ├── ai_analysis.html        # AI analiz
│   ├── arac_yonetimi.html      # Araç yönetimi
│   └── ...
└── docs/
    ├── VERI_YUKLEME_REHBERI.md # Detaylı yükleme rehberi
    ├── DEPLOY_REHBERI.md        # Deployment rehberi
    └── README_FINAL.md          # Bu dosya
```

---

## 🎯 ANA ÖZELLİKLER

### 1. 📤 Veri Yükleme (YENİ!)
- Web arayüzünden Excel yükleme
- Sürükle-bırak desteği
- 3 tip: Yakıt, Ağırlık, Araç Takip
- Otomatik kolon eşleştirme
- Duplicate kontrolü

### 2. 📊 Analiz Sistemleri
- **Yakıt Analizi**: KM/Litre, toplam tüketim
- **Ağırlık Analizi**: Ton/Litre, sefer verimliliği
- **Performans Karşılaştırma**: Araç bazlı

### 3. 🤖 AI Özellikleri
- Yakıt tüketim tahmini
- Anomali tespiti
- Toplu plaka analizi
- Chatbot asistan (Ollama)

### 4. 🚛 Araç Yönetimi
- Araç ekleme/düzenleme/silme
- Toplu işlemler
- Binek/Kargo/İş Makinesi filtreleme

### 5. 💰 Muhasebe
- Gelir-gider hesaplama
- Plaka bazlı kar analizi
- PDF/Excel export

---

## 📊 DESTEKLENEN EXCEL FORMATLARI

### ⛽ Yakıt Excel
**Zorunlu Kolonlar:**
- `plaka`
- `islem_tarihi` veya `tarih`
- `yakit_miktari` veya `miktar`

**Opsiyonel:**
- `birim_fiyat`, `satir_tutari`, `km_bilgisi`, `stok_adi`

### ⚖️ Ağırlık Excel
**Zorunlu:**
- `plaka`, `tarih`, `miktar`, `birim`

**Opsiyonel:**
- `net_agirlik`, `adres`, `cari_adi`

### 🚛 Araç Takip Excel
**Zorunlu:**
- `plaka`, `tarih`

**Opsiyonel:**
- `toplam_kilometre`, `gunluk_yakit_tuketimi_l`, `sofor_adi`

**💡 İpucu:** Kolon isimleri büyük/küçük harf ve Türkçe karakter duyarsız!

---

## 🌐 DEPLOY (Render.com)

### Adım 1: GitHub'a Push
```bash
git add .
git commit -m "Supabase + Web upload ready"
git push origin main
```

### Adım 2: Render.com
1. **New Web Service** oluşturun
2. GitHub repo'nuzu seçin
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn app:app`

### Adım 3: Environment Variables
Render dashboard'da ekleyin:
```
VITE_SUPABASE_URL=https://qlwycqwquapwwgfysscy.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGci...
PYTHON_VERSION=3.11.0
```

### Adım 4: İlk Veri Yükleme
Deploy tamamlandıktan sonra:
```
https://your-app.onrender.com/veri-yukleme
```

Excel dosyalarınızı yükleyin!

---

## 📖 DOKÜMANTASYON

- **[Veri Yükleme Rehberi](VERI_YUKLEME_REHBERI.md)**: Excel yükleme detayları
- **[Deploy Rehberi](DEPLOY_REHBERI.md)**: Render.com deployment
- **[Supabase Notları](SUPABASE_MIGRATION_NOTES.md)**: Teknik detaylar

---

## 🔧 TEKNOLOJİLER

- **Backend**: Flask 3.0 + Python 3.11
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Vanilla JS + Bootstrap 5
- **AI**: scikit-learn + Ollama
- **Deploy**: Render.com
- **Dosya İşleme**: Pandas + openpyxl

---

## 💡 GÜNLÜK KULLANIM

### Sabah Rutini (2 dakika)
1. `https://your-app.onrender.com/veri-yukleme` aç
2. Dün gece indirilen Excel dosyalarını sürükle
3. "Yüklendi ✅" mesajını bekle
4. Bitti! Analizler otomatik güncellendi

### Haftalık Kontrol
1. Ana sayfadan "📊 Performans Analizi" tıkla
2. En verimli/verimsiz araçları gör
3. PDF export yap, müdüre göster

### Aylık Muhasebe
1. "💰 Muhasebe Analizi" menüsü
2. Tarih aralığı seç
3. Excel indir, muhasebeciye gönder

---

## 🆘 YARDIM & DESTEK

### Sık Sorulan Sorular

**S: Excel yüklenmiyor?**
**C:** Dosya `.xlsx` veya `.xls` olmalı. "Farklı Kaydet" → "Excel Workbook" yapın.

**S: Duplicate kayıtlar ekleniyor mu?**
**C:** Hayır! Sistem otomatik duplicate kontrol yapar ve atlar.

**S: Hangi kolonlar zorunlu?**
**C:** Sadece `plaka` + tarih kolonları zorunlu. Diğerleri opsiyonel.

**S: Türkçe karakterler sorun olur mu?**
**C:** Hayır! Sistem otomatik düzeltir: `İşlem Tarihi` → `islem_tarihi`

### Hata Ayıklama

1. **Flask Terminali**: Sunucu loglarını kontrol edin
2. **Browser Console (F12)**: JavaScript hatalarını görün
3. **Supabase Dashboard**: Veritabanı loglarını inceleyin

---

## 📞 İLETİŞİM

Sorun yaşarsanız:
1. GitHub Issues'da bildirin
2. Excel örnek dosyası ekleyin
3. Hata mesajını paylaşın

---

## 🎉 SONUÇ

Artık günlük Excel yüklemesi **10 saniye**! Komut satırına veda edin, web arayüzünü kullanın! 🚀

**Happy Analyzing!** 📊✨
