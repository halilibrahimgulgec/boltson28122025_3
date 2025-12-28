# Railway Hızlı Deploy Kılavuzu

## 5 Dakikada Railway'e Deploy

### 1️⃣ Git Hazırla (1 dk)

```bash
git init
git add .
git commit -m "Initial commit"
```

### 2️⃣ GitHub'a Push (1 dk)

```bash
# GitHub'da yeni repo oluştur: kargo-yakit-analiz
git remote add origin https://github.com/KULLANICI_ADINIZ/kargo-yakit-analiz.git
git branch -M main
git push -u origin main
```

### 3️⃣ Railway'de Deploy (2 dk)

1. https://railway.app → Login with GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Repository seç: `kargo-yakit-analiz`
4. **Variables** sekmesine git:
   ```
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   ```
5. **Settings** → **Generate Domain**

### 4️⃣ Test (1 dk)

```
https://kargo-yakit-analiz-production.up.railway.app
```

✅ Ana sayfa: 82,563 kayıt görünmeli
✅ Binek Araç: 112 araç listesi
✅ Muhasebe: Raporlar çalışmalı

## Tek Komut Deploy

```bash
# Değişiklik yap, sonra:
git add . && git commit -m "Update" && git push
```

Railway otomatik yeniden deploy eder!

## Kritik Kontrol

```bash
# Railway Variables kontrol:
✅ VITE_SUPABASE_URL
✅ VITE_SUPABASE_ANON_KEY

# Supabase'de veri var mı?
- 32,942 yakıt kaydı
- 42,034 ağırlık kaydı
- 146 araç tanımı
```

## Sorun mu Var?

**Supabase hata:**
→ Variables'a credentials ekle

**Build hatası:**
→ `git push` yap, Railway otomatik rebuild eder

**Domain çalışmıyor:**
→ Settings → Generate Domain → Yenile

## Tamamlandı! 🎉

Railway URL'iniz:
```
https://your-app-production.up.railway.app
```

Program **Supabase** ile çalışıyor, tüm veriler güvende!
