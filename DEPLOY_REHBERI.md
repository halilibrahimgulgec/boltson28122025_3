# Render.com'a Deploy Rehberi

## 📋 ÖN HAZIRLIK

### 1. Excel Verilerini Supabase'e Yükle

Önce verilerinizi Supabase'e yüklemeniz gerekiyor:

```bash
python3 upload_excel_to_supabase.py
```

Script size 3 Excel dosyası soracak:
- ⛽ Yakıt Excel dosyası
- ⚖️ Ağırlık Excel dosyası
- 🚛 Araç takip Excel dosyası

Her birinin dosya adını yazın (örn: `yakit.xlsx`). Boş bırakırsanız o tablo atlanır.

### 2. Verileri Kontrol Et

```bash
python3 -c "from database import get_database_info, get_statistics; info = get_database_info(); print('Yakıt:', info.get('yakit_count')); stats = get_statistics(); print('Toplam Yakıt:', stats.get('toplam_yakit'), 'L')"
```

Eğer "Toplam Yakıt: 0 L" görürseniz, veriler yüklenmemiş demektir. Adım 1'e dönün.

---

## 🚀 RENDER.COM'A DEPLOY

### Adım 1: GitHub'a Push

```bash
git add .
git commit -m "Supabase entegrasyonu tamamlandı"
git push origin main
```

### Adım 2: Render.com'da Yeni Web Service Oluştur

1. [Render.com](https://render.com)'a gidin
2. **New +** → **Web Service**
3. GitHub repo'nuzu seçin
4. Ayarlar:
   - **Name**: `kargo-takip` (veya istediğiniz isim)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### Adım 3: Environment Variables Ekle

**Environment** sekmesinde şu değişkenleri ekleyin:

```
VITE_SUPABASE_URL=https://qlwycqwquapwwgfysscy.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsd3ljcXdxdWFwd3dnZnlzc2N5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MTY0MTcsImV4cCI6MjA3NDk5MjQxN30.zSxr_iw0E6wS8fSebX4gFh_YYv2GYDU3UtRj_N2o4qY
PYTHON_VERSION=3.11.0
```

### Adım 4: Deploy

**Create Web Service** butonuna tıklayın. Deploy işlemi 5-10 dakika sürer.

---

## ✅ DEPLOY SONRASI

Deploy tamamlandığında, Render size bir URL verecek:

```
https://kargo-takip.onrender.com
```

Bu URL'yi tarayıcınızda açın ve uygulamanızı test edin!

---

## 🔧 SORUN GİDERME

### "Internal Server Error" Hatası

**Logs** sekmesini kontrol edin. Genelde şu sebeplerden olur:

1. **Environment variables eksik**: `.env` değişkenlerini Render'a eklediniz mi?
2. **Supabase verisi yok**: Adım 1'deki Excel yükleme işlemini yaptınız mı?

### Veritabanı Bağlantı Hatası

```bash
# Lokal test
python3 -c "from database import get_database_info; print(get_database_info())"
```

Eğer hata alırsanız, `.env` dosyanızda Supabase bilgileri doğru mu kontrol edin.

---

## 📊 ÖZELLİKLER

✅ Supabase PostgreSQL veritabanı (kalıcı)
✅ Render.com hosting (ücretsiz)
✅ Otomatik SSL sertifikası
✅ Git push ile otomatik deploy
✅ Sınırsız trafik (free tier'da)

---

## 💡 İPUÇLARI

1. **Free tier**: İlk 750 saat/ay ücretsiz. Sonra uyku moduna girer.
2. **Cold start**: 15 dakika kullanılmazsa uyur, ilk istek 30-60 saniye sürebilir.
3. **Database**: Supabase'deki veriler kalıcı, Render restart'ta silinmez.

---

## 📞 DESTEK

Sorun yaşarsanız:
- Render logs: `https://dashboard.render.com/web/[service-id]/logs`
- Supabase logs: `https://supabase.com/dashboard/project/[project-id]/logs`
