# ⚡ Hızlı Render.com Deployment

5 dakikada deploy edin!

---

## 🚀 5 ADIMDA DEPLOYMENT

### 1️⃣ GitHub'a Push (2 dakika)

```bash
# Repoyu başlatın
git init
git add .
git commit -m "Initial commit"

# GitHub'a yükleyin (https://github.com/new adresinde repo oluşturun)
git remote add origin https://github.com/KULLANICI_ADI/kargo-takip.git
git branch -M main
git push -u origin main
```

---

### 2️⃣ Render.com'a Giriş (30 saniye)

1. https://render.com → **Sign In**
2. **GitHub** ile giriş yapın

---

### 3️⃣ Web Service Oluştur (1 dakika)

1. **New +** → **Web Service**
2. GitHub reponuzu seçin
3. Ayarlar (otomatik dolu olmalı):
   ```
   Name: kargo-takip
   Runtime: Python 3
   Build: pip install -r requirements.txt
   Start: gunicorn app:app --bind 0.0.0.0:$PORT
   ```
4. Plan: **Free** (test için) veya **Starter** (production için)

---

### 4️⃣ Environment Variables Ekle (1 dakika)

**Environment** sekmesinde şunları ekleyin:

```bash
VITE_SUPABASE_URL=https://qlwycqwquapwwgfysscy.supabase.co

VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsd3ljcXdxdWFwd3dnZnlzc2N5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MTY0MTcsImV4cCI6MjA3NDk5MjQxN30.zSxr_iw0E6wS8fSebX4gFh_YYv2GYDU3UtRj_N2o4qY
```

---

### 5️⃣ Deploy! (5 dakika)

**Create Web Service** tıklayın ve bekleyin.

Deploy tamamlandığında:
```
✅ Live at: https://kargo-takip.onrender.com
```

---

## ✅ TAMAMLANDI!

Uygulamanız artık canlı!

### Test Edin:
```
https://kargo-takip.onrender.com
```

### Verileri Yükleyin:
```
https://kargo-takip.onrender.com/veri-yukleme
```

---

## 🔄 Güncelleme için:

```bash
# Kod değişikliği yaptınız mı?
git add .
git commit -m "Güncelleme"
git push

# Render otomatik deploy eder!
```

---

## ⚠️ Free Plan Notu

- İlk açılış **30-60 saniye** sürebilir (uyku modundan uyanma)
- 15 dakika aktivite yoksa uyur
- Production için **Starter Plan** ($7/ay) önerilir

---

## 📚 Detaylı Rehber

Daha fazla bilgi için: **RENDER_DEPLOYMENT.md**

**Başarılar!** 🎉
