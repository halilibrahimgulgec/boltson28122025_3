# 🚀 Render.com Deployment Rehberi

Bu rehber, Kargo Takip uygulamanızı Render.com'a nasıl deploy edeceğinizi adım adım gösterir.

---

## 📋 ÖN GEREKSINIMLER

- ✅ GitHub hesabı
- ✅ Render.com hesabı (ücretsiz)
- ✅ Supabase database (zaten hazır!)
- ✅ Proje dosyaları (bu repo)

---

## 🎯 ADIM ADIM DEPLOYMENT

### Adım 1: GitHub'a Yükleyin

#### 1.1 Git Repo Oluşturun (ilk kez ise)

```bash
cd /tmp/cc-agent/57925605/project

# Git başlat
git init

# Dosyaları ekle
git add .
git commit -m "Initial commit - Kargo Takip App"
```

#### 1.2 GitHub'da Yeni Repo Oluşturun

1. GitHub'da gidin: https://github.com/new
2. Repository name: `kargo-takip-app` (veya istediğiniz isim)
3. **Public** veya **Private** seçin
4. **Create repository** tıklayın

#### 1.3 GitHub'a Push Edin

```bash
# GitHub repo URL'nizi ekleyin (örnek)
git remote add origin https://github.com/KULLANICI_ADINIZ/kargo-takip-app.git

# Main branch'e push edin
git branch -M main
git push -u origin main
```

---

### Adım 2: Render.com'da Proje Oluşturun

#### 2.1 Render'a Giriş Yapın

1. https://render.com adresine gidin
2. **Sign In** (veya **Get Started** yeni hesapsa)
3. GitHub hesabınızla giriş yapın

#### 2.2 New Web Service Oluşturun

1. Dashboard'da **New +** butonuna tıklayın
2. **Web Service** seçin
3. GitHub reponuzu seçin (kargo-takip-app)
   - Eğer görmüyorsanız: **Configure account** ile GitHub bağlantısını yapın

---

### Adım 3: Web Service Ayarları

Render otomatik olarak `render.yaml` dosyasını algılayacak, ama manuel kontrol edin:

#### 3.1 Temel Ayarlar

```
Name: kargo-takip
Runtime: Python 3
Region: Frankfurt (veya size en yakın)
Branch: main
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
```

#### 3.2 Plan Seçimi

- **Free** (Ücretsiz başlamak için)
  - ⚠️ 15 dakika aktivite yoksa uyur
  - ⚠️ 750 saat/ay limit
  - ✅ SSL otomatik
  - ✅ Yeterli test için

- **Starter ($7/ay)** (Production için önerilen)
  - ✅ Hiç uyumaz
  - ✅ Unlimited saat
  - ✅ Daha hızlı

---

### Adım 4: Environment Variables Ekleyin

**ÇOK ÖNEMLİ!** Render'da şu environment variables'ları ekleyin:

#### 4.1 Render Dashboard'da

1. Web Service'inizi açın
2. **Environment** sekmesine gidin
3. Şu değişkenleri **Add Environment Variable** ile ekleyin:

```bash
# Supabase Bağlantısı (ZORUNLU)
VITE_SUPABASE_URL=https://qlwycqwquapwwgfysscy.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsd3ljcXdxdWFwd3dnZnlzc2N5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MTY0MTcsImV4cCI6MjA3NDk5MjQxN30.zSxr_iw0E6wS8fSebX4gFh_YYv2GYDU3UtRj_N2o4qY

# Python Version (Opsiyonel)
PYTHON_VERSION=3.13.0

# Port (Otomatik ayarlanır, opsiyonel)
PORT=10000
```

#### 4.2 Nasıl Eklerim?

Her değişken için:
1. **Key** kutusuna: `VITE_SUPABASE_URL`
2. **Value** kutusuna: `https://qlwycqwquapwwgfysscy.supabase.co`
3. **Add** tıklayın
4. Diğerleri için tekrarlayın

---

### Adım 5: Deploy Edin

#### 5.1 Manuel Deploy

1. **Deploy** butonuna tıklayın
2. Logs'u izleyin (Deploy Logs)
3. Build süreci:
   ```
   Installing requirements...
   ✓ Flask yüklendi
   ✓ Pandas yüklendi
   ✓ Gunicorn yüklendi
   Starting server...
   ```

#### 5.2 Deploy Süresi

- **İlk deploy:** ~5-10 dakika
- **Sonraki deploylar:** ~2-3 dakika

#### 5.3 Başarılı Deploy

Görmelisiniz:
```
✅ Build successful
✅ Deploy live at: https://kargo-takip.onrender.com
```

---

### Adım 6: Test Edin

#### 6.1 Uygulamayı Açın

```
https://kargo-takip.onrender.com
```

veya Render'ın size verdiği URL.

#### 6.2 İlk Açılış (Free Plan'da)

⚠️ **Free plan 15 dakika sonra uyur**, ilk açılış **30-60 saniye** sürebilir.

#### 6.3 Test Checklist

- [ ] Ana sayfa açılıyor mu?
- [ ] Veritabanı durumu görünüyor mu? (2912 yakıt, 8757 ağırlık vb.)
- [ ] Veri yükleme sayfası çalışıyor mu?
- [ ] Excel upload ediliyor mu?
- [ ] Analizler çalışıyor mu?

---

## 🔄 GÜNCELLEME (Yeni Kod Push)

### Lokal değişiklik yaptıktan sonra:

```bash
# Değişiklikleri commit edin
git add .
git commit -m "Yeni özellik eklendi"
git push origin main
```

Render **otomatik deploy** başlatır! (GitHub integration sayesinde)

---

## 🐛 SORUN GIDERME

### 1. "Application Error" Görüyorum

**Neden:** Environment variables eksik veya yanlış.

**Çözüm:**
1. Render Dashboard → Environment
2. `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY` kontrol edin
3. **Save Changes** → Otomatik redeploy

### 2. "Build Failed" Hatası

**Neden:** `requirements.txt` sorunu.

**Çözüm:**
```bash
# Lokal test edin
pip install -r requirements.txt
python app.py
```

Hata yoksa:
```bash
git add requirements.txt
git commit -m "Fix requirements"
git push
```

### 3. "502 Bad Gateway"

**Neden:** Uygulama başlamadı.

**Çözüm:**
1. Render Logs'u kontrol edin
2. `gunicorn app:app` komutu çalışıyor mu?
3. Port binding doğru mu?

```bash
# Lokal test
gunicorn app:app --bind 0.0.0.0:8000
```

### 4. Veritabanı Bağlanamıyor

**Neden:** Supabase credentials yanlış.

**Çözüm:**
1. `.env` dosyanızı kontrol edin
2. Supabase Dashboard → Settings → API
3. URL ve ANON_KEY'i doğrulayın
4. Render'da güncelleyin

### 5. Free Plan Çok Yavaş

**Çözüm:**
- **Starter Plan'e** yükseltin ($7/ay)
- Veya başka bir servis: **Railway.app**, **Fly.io**

---

## 📊 PERFORMANS İPUÇLARI

### Free Plan için:

1. **Health Check URL** ekleyin (uyumaması için):
   - UptimeRobot kullanın: https://uptimerobot.com
   - 5 dakikada bir ping at

2. **Disk Kullanımını Azaltın:**
   - SQLite yerine sadece Supabase kullanın
   - `kargo_data.db` dosyasını kaldırın (zaten Supabase'de var)

### Production için:

1. **Starter Plan** kullanın
2. **Caching** ekleyin (Redis)
3. **CDN** kullanın (static dosyalar için)

---

## 🔒 GÜVENLİK

### YAPMAMALISINIZ:

❌ `.env` dosyasını GitHub'a push etmeyin
❌ ANON_KEY'i public kodda göstermeyin
❌ Database credentials'ları expose etmeyin

### YAPMALISINIZ:

✅ `.gitignore` dosyasında `.env` var mı kontrol edin
✅ Environment variables'ı sadece Render'da saklayın
✅ Supabase RLS politikalarını aktif tutun

---

## 📈 MONİTORİNG

### Render Dashboard'da:

1. **Metrics** → CPU, Memory, Requests
2. **Logs** → Hata logları
3. **Events** → Deploy history

### Supabase Dashboard'da:

1. **Database** → Tablo boyutları
2. **API** → Request statistics
3. **Logs** → Query performance

---

## 💰 MALİYET TAHMİNİ

### Free Plan:
```
Render Free: $0/ay
Supabase Free: $0/ay (500 MB database)
TOPLAM: $0/ay
```

### Production Plan:
```
Render Starter: $7/ay
Supabase Pro: $25/ay (8 GB database, günlük backup)
TOPLAM: $32/ay
```

---

## 🎉 TAMAMLANDI!

Artık uygulamanız canlıda!

**URL'nizi paylaşın:**
```
https://kargo-takip.onrender.com
```

### Sonraki Adımlar:

1. ✅ Custom domain ekleyin (render.com docs)
2. ✅ Analytics ekleyin (Google Analytics)
3. ✅ Monitoring ekleyin (Sentry)
4. ✅ Backup stratejisi oluşturun

---

## 📚 EK KAYNAKLAR

- Render Docs: https://render.com/docs
- Supabase Docs: https://supabase.com/docs
- Flask Production: https://flask.palletsprojects.com/en/latest/deploying/
- Gunicorn Config: https://docs.gunicorn.org/en/stable/settings.html

---

**Sorularınız mı var?**
Render Community: https://community.render.com
Supabase Discord: https://discord.supabase.com

**Başarılar!** 🚀
