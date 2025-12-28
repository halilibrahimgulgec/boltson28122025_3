# 🚀 BULUTA AKTARIM REHBERİ

## ÖNEMLİ: GİTHUB'A YÜKLE

### 1. GitHub Hesabı Oluştur (yoksa)
- https://github.com adresine git
- "Sign up" ile hesap oluştur

### 2. Yeni Repository (Depo) Oluştur
- GitHub'da "New repository" tıkla
- İsim: `kargo-takip` (veya istediğin isim)
- **Public** veya **Private** seç
- **"Add .gitignore" SEÇMEYİN** (bizde zaten var)
- "Create repository" tıkla

### 3. Yerel Projeyi GitHub'a Yükle

Terminal'de projenin klasöründe:

```bash
# GitHub'dan aldığın URL'i buraya yaz
git remote add origin https://github.com/KULLANICI_ADIN/kargo-takip.git

# Ana branch ismini main yap
git branch -M main

# GitHub'a yükle
git push -u origin main
```

GitHub kullanıcı adı ve şifre/token ister, gir.

---

## RENDER.COM'A DEPLOY ET

### 1. Render Hesabı Oluştur
- https://render.com adresine git
- "Get Started for Free" tıkla
- GitHub hesabınla giriş yap

### 2. Yeni Web Service Oluştur
- Dashboard'da "New +" tıkla
- "Web Service" seç
- GitHub repository'ni bağla
- `kargo-takip` repository'sini seç

### 3. Ayarları Yap

**Render otomatik algılayacak ama kontrol et:**

- **Name**: kargo-takip (istediğin ismi ver)
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`

### 4. Environment Variables (Ortam Değişkenleri)

Render'da "Environment" sekmesinde bu değişkenleri ekle:

```
VITE_SUPABASE_URL = https://qlwycqwquapwwgfysscy.supabase.co
VITE_SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsd3ljcXdxdWFwd3dnZnlzc2N5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MTY0MTcsImV4cCI6MjA3NDk5MjQxN30.zSxr_iw0E6wS8fSebX4gFh_YYv2GYDU3UtRj_N2o4qY
SECRET_KEY = (Render otomatik oluşturacak veya kendim random bir değer gir)
PYTHON_VERSION = 3.11.0
```

### 5. Deploy Et!
- "Create Web Service" tıkla
- Render otomatik build edip deploy edecek
- 5-10 dakika sonra hazır!

---

## UYGULAMA LİNKİ

Render sana şöyle bir link verecek:

```
https://kargo-takip.onrender.com
```

Bu linki tarayıcıda aç ve uygulamayı kullan!

---

## ÖNEMLİ NOTLAR

### ✅ Ücretsiz Plan
- Render'ın ücretsiz planı 750 saat/ay
- 15 dakika hareketsiz kalırsa uyku moduna girer
- İlk ziyaret 30-60 saniye sürebilir (uyanma süresi)

### ✅ Güncelleme Yap
Projeyi güncelledikten sonra:

```bash
git add .
git commit -m "Güncelleme açıklaması"
git push
```

Render otomatik yeni versiyonu deploy eder!

### ✅ Logları Gör
Render dashboard'da "Logs" sekmesinden hatalar ve logları görebilirsin.

---

## ALTERNATIF: RAILWAY.APP

Railway de iyi bir alternatif:

1. https://railway.app git
2. GitHub ile giriş yap
3. "New Project" → "Deploy from GitHub repo" seç
4. Aynı environment variables'ları ekle
5. Deploy!

Railway de otomatik algılar ve deploy eder.

---

## SORUN ÇÖZME

### Hata: "Module not found"
- `requirements.txt` dosyasını kontrol et
- Render build loglarını incele

### Hata: "Database connection failed"
- Environment variables'ların doğru girildiğini kontrol et
- Supabase URL ve KEY'i kopyala-yapıştır yap

### Hata: "Application failed to respond"
- `gunicorn app:app` komutunun doğru olduğunu kontrol et
- Port binding: `--bind 0.0.0.0:$PORT` olmalı

---

## BAŞARILI! 🎉

Artık uygulamana dünyanın her yerinden erişebilirsin!
