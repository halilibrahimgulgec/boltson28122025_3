# Railway Deployment Talimatları

## Ön Hazırlık

### 1. Git Repository Oluştur

```bash
# Git init (eğer yoksa)
git init

# Tüm dosyaları ekle
git add .

# İlk commit
git commit -m "Initial commit - Kargo Yakıt Analiz Sistemi"
```

### 2. GitHub'a Push

```bash
# GitHub'da yeni repository oluştur: kargo-yakit-analiz

# Remote ekle
git remote add origin https://github.com/KULLANICI_ADINIZ/kargo-yakit-analiz.git

# Push et
git branch -M main
git push -u origin main
```

## Railway Deployment

### 1. Railway Hesabı
- https://railway.app/ adresine git
- GitHub ile giriş yap

### 2. Yeni Proje Oluştur
1. "New Project" butonuna tıkla
2. "Deploy from GitHub repo" seç
3. Repository'nizi seçin: `kargo-yakit-analiz`
4. Railway otomatik olarak Python + Flask'ı algılayacak

### 3. Environment Variables Ekle

Railway Dashboard'da **"Variables"** sekmesine git ve şu değişkenleri ekle:

```bash
# Supabase Credentials (ZORUNLU)
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Alternatif isimler (destekleniyor)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANAHTAR=your-anon-key-here

# Flask ayarları
FLASK_ENV=production
PORT=5000
```

**ÖNEMLİ:** Supabase credentials olmadan program çalışmayacak!

### 4. Deploy

Railway otomatik deploy başlatacak. Kontrol için:

1. **"Deployments"** sekmesinden ilerlemeyi izle
2. **"Logs"** sekmesinden hataları kontrol et
3. Deploy başarılı olunca **"Settings"** → **"Generate Domain"** ile URL al

### 5. Domain

Railway size otomatik bir domain verir:
```
https://kargo-yakit-analiz-production.up.railway.app
```

## Supabase Verilerini Kontrol

Railway'de çalışan uygulama **direkt Supabase**'i kullanır:
- Tüm veriler Supabase'de
- SQLite kullanılmaz
- Her deployment'ta veriler korunur

### Test

1. Railway URL'i aç
2. Ana sayfada istatistikleri gör:
   - 82,563 toplam kayıt
   - 32,942 yakıt kaydı
   - 42,034 ağırlık kaydı
   - 142 plaka

3. "Binek Araç Analizi" butonuna tıkla
4. 112 binek araç listesini gör

## Sorun Giderme

### Hata: "Supabase credentials bulunamadı"
**Çözüm:** Railway Variables'a `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY` ekle

### Hata: "ModuleNotFoundError"
**Çözüm:** `requirements.txt` güncel mi kontrol et
```bash
git add requirements.txt
git commit -m "Update requirements"
git push
```

### Hata: Port binding
**Çözüm:** `Procfile` doğru mu kontrol et:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

### Logs Nasıl Görülür?
Railway Dashboard → Deployments → View Logs

### Yeniden Deploy
```bash
git add .
git commit -m "Update"
git push
```
Railway otomatik yeniden deploy eder.

## Önemli Notlar

1. **SQLite Kullanma:** Railway ephemeral storage kullanır, her restart'ta SQLite sıfırlanır
2. **Supabase Zorunlu:** Tüm veriler Supabase'de olmalı
3. **Environment Variables:** Her deploy sonrası variables'ı kontrol et
4. **Build Time:** İlk deploy 2-3 dakika sürebilir
5. **Free Tier:** Railway free tier 500 saat/ay verir

## Başarı Kriterleri

✅ Ana sayfa açılıyor
✅ Veritabanı istatistikleri görünüyor (82,563 kayıt)
✅ Plaka listesi yükleniyor
✅ Binek araç analizi çalışıyor
✅ Muhasebe raporu çalışıyor
✅ AI asistan çalışıyor (Ollama Railway'de çalışmaz - bu normal)

## Railway Deployment Özeti

```bash
# 1. Git hazırla
git add .
git commit -m "Railway deployment"
git push origin main

# 2. Railway'de
- New Project → GitHub → Repository seç
- Variables → VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY ekle
- Deploy → Domain oluştur
- Test et!
```

**Tebrikler!** Uygulamanız Railway'de çalışıyor 🚀
