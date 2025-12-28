# Bulut Deployment Rehberi

Bu proje Supabase veritabanı ile çalışan Flask tabanlı bir yakıt takip sistemidir.

## Gereksinimler

- Python 3.11+
- Supabase hesabı
- Railway veya Render hesabı (bulut deployment için)

## Önemli Dosyalar

- `app.py` - Ana Flask uygulaması
- `database.py` - Supabase veritabanı işlemleri
- `requirements.txt` - Python bağımlılıkları
- `Procfile` - Deployment komutu
- `runtime.txt` - Python versiyonu
- `.env` - Çevre değişkenleri (GİZLİ TUTUN!)

## Supabase Veritabanı Tabloları

Projenizde şu tablolar olmalı:

1. **yakit** - Yakıt alım kayıtları
   - plaka (text)
   - yakit_miktari (numeric)
   - satir_tutari (numeric)
   - islem_tarihi (date)
   - km_bilgisi (numeric)
   - birim_fiyat (numeric)

2. **agirlik** - Yük ağırlık kayıtları
   - plaka (text)
   - miktar (numeric)
   - net_agirlik (numeric)
   - tarih (date)
   - birim (text)
   - ana_malzeme (text)

3. **araclar** - Araç bilgileri
   - plaka (text, primary key)
   - sahip (text) - 'BİZİM' veya 'TAŞERON'
   - arac_tipi (text) - 'KARGO ARACI', 'BİNEK ARAÇ', 'İŞ MAKİNESİ'
   - aktif (integer) - 1=aktif, 0=pasif
   - notlar (text)
   - created_at (timestamp)
   - updated_at (timestamp)

4. **arac_takip** - Araç takip kayıtları (opsiyonel)
5. **processed_files** - İşlenen dosya kayıtları (opsiyonel)

## Railway Deployment

1. Railway hesabı oluşturun: https://railway.app
2. GitHub'a projeyi yükleyin
3. Railway'de "New Project" > "Deploy from GitHub"
4. Projenizi seçin
5. Çevre değişkenlerini ekleyin:
   ```
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_key
   SECRET_KEY=your_secret_key
   ```
6. Deploy butonuna tıklayın

## Render Deployment

1. Render hesabı oluşturun: https://render.com
2. "New Web Service" seçin
3. GitHub reponuzu bağlayın
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Çevre değişkenlerini ekleyin
7. "Create Web Service" tıklayın

## Çevre Değişkenleri (.env)

```env
VITE_SUPABASE_ANON_KEY=your_anon_key_here
VITE_SUPABASE_URL=https://yourproject.supabase.co
SECRET_KEY=your_secret_key_here
```

**UYARI:** `.env` dosyasını GitHub'a yüklemeyin! `.gitignore` dosyasına ekli olduğundan emin olun.

## Yerel Test

```bash
# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı başlat
python app.py
```

Tarayıcıda açın: http://localhost:5000

## Özellikler

- ✅ Kargo araçları analizi
- ✅ Binek araç analizi
- ✅ İş makinesi analizi
- ✅ Muhasebe raporu
- ✅ Performans karşılaştırma
- ✅ Excel/PDF export
- ✅ Araç yönetimi
- ✅ Veri yükleme
- ✅ AI analiz (opsiyonel)

## Sorun Giderme

1. **Supabase bağlantı hatası**: `.env` dosyasındaki URL ve KEY'leri kontrol edin
2. **Tablo bulunamadı hatası**: Supabase'de tabloları oluşturun
3. **Build hatası**: `requirements.txt` dosyasını kontrol edin
4. **Port hatası**: Railway/Render otomatik PORT değişkeni atar

## Destek

Sorunlar için GitHub Issues kullanın.
