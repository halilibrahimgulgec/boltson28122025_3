# ✅ Deployment Checklist

Deploy öncesi bu listeyi kontrol edin!

---

## 📋 PRE-DEPLOYMENT

### Kod Hazırlığı
- [x] `render.yaml` dosyası var
- [x] `requirements.txt` güncel
- [x] `.gitignore` dosyasında `.env` var
- [x] `database.py` environment variables kullanıyor
- [x] Gunicorn yüklü (`requirements.txt`'de var)
- [x] Port binding doğru (`--bind 0.0.0.0:$PORT`)

### Güvenlik
- [x] `.env` dosyası `.gitignore`'da
- [x] Supabase credentials hardcoded değil
- [x] SQLite database `.gitignore`'da (`*.db`)
- [x] `__pycache__` `.gitignore`'da

### Test (Lokal)
- [ ] `python app.py` çalışıyor
- [ ] `gunicorn app:app` çalışıyor
- [ ] Veritabanı bağlantısı çalışıyor
- [ ] Excel upload çalışıyor
- [ ] Analizler çalışıyor

---

## 🚀 DEPLOYMENT

### GitHub
- [ ] Repo oluşturuldu
- [ ] Kod push edildi
- [ ] `.env` push edilmedi (confirm)

### Render.com
- [ ] Hesap oluşturuldu
- [ ] GitHub bağlandı
- [ ] Web Service oluşturuldu
- [ ] Python runtime seçildi

### Environment Variables (Render'da)
- [ ] `VITE_SUPABASE_URL` eklendi
- [ ] `VITE_SUPABASE_ANON_KEY` eklendi
- [ ] `PYTHON_VERSION=3.13.0` eklendi

### Build & Deploy
- [ ] Deploy başlatıldı
- [ ] Build logs kontrol edildi
- [ ] Deploy başarılı (✅ Live)

---

## 🧪 POST-DEPLOYMENT

### Temel Testler
- [ ] Ana sayfa açılıyor: `https://APP_URL.onrender.com`
- [ ] Veritabanı durumu görünüyor
- [ ] Veri yükleme sayfası açılıyor: `/veri-yukleme`
- [ ] Excel dosyası yükleniyor
- [ ] Analizler çalışıyor: `/ai-analysis`
- [ ] Muhasebe sayfası çalışıyor: `/muhasebe`

### Veritabanı Testleri
- [ ] Supabase bağlantısı çalışıyor
- [ ] Yakıt kayıtları görünüyor (2912)
- [ ] Ağırlık kayıtları görünüyor (8757)
- [ ] Araç takip kayıtları görünüyor (2781)
- [ ] Plaka sayısı doğru (125)

### Performans
- [ ] İlk yükleme süresi < 2 saniye (Starter Plan)
- [ ] İlk yükleme süresi < 60 saniye (Free Plan - cold start)
- [ ] API yanıt süresi < 1 saniye
- [ ] Excel upload < 5 saniye

### Hata Durumları
- [ ] 404 sayfası çalışıyor
- [ ] 500 hatası yok
- [ ] Logs'da error yok
- [ ] Database timeout yok

---

## 🐛 SORUN GIDERME

### Build Başarısız
```bash
# Lokal test
pip install -r requirements.txt
python app.py

# Sorun varsa requirements.txt'i düzelt
pip freeze > requirements.txt
```

### Deploy Başarılı ama App Çalışmıyor
1. Render Logs kontrol edin
2. Environment variables kontrol edin
3. Gunicorn komutu doğru mu?
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```

### Database Bağlanamıyor
1. Environment variables doğru mu?
   ```bash
   VITE_SUPABASE_URL=https://...
   VITE_SUPABASE_ANON_KEY=eyJh...
   ```
2. Supabase'de RLS politikaları aktif mi?
3. Supabase API key geçerli mi?

---

## 📊 MONİTORİNG

### Günlük Kontroller
- [ ] App erişilebilir mi?
- [ ] Response time normal mi?
- [ ] Error rate düşük mü?

### Haftalık Kontroller
- [ ] Disk kullanımı < 512 MB (Free Plan)
- [ ] Database boyutu < 500 MB (Supabase Free)
- [ ] API request sayısı < 50K/gün (Supabase Free)

### Aylık Kontroller
- [ ] Backup alındı mı?
- [ ] Dependencies güncel mi?
- [ ] Security patches uygulandı mı?

---

## 💰 MALİYET KONTROLÜ

### Free Plan Limitler
- ✅ Render: 750 saat/ay
- ✅ Supabase: 500 MB database, 2 GB bandwidth/ay
- ⚠️ 15 dakika inaktivite sonrası uyku

### Upgrade Zamanı
Şu durumda Starter Plan'e geçin ($7/ay):
- ❌ App sürekli uyuyor
- ❌ Cold start süresi uzun
- ❌ Kullanıcı sayısı > 10
- ❌ Günlük request > 1000

---

## 🎉 TAMAMLANDI!

Tüm checklistler ✅ ise deployment başarılı!

### Sonraki Adımlar:
1. Custom domain ekleyin
2. Analytics ekleyin (Google Analytics)
3. Monitoring ekleyin (Sentry, UptimeRobot)
4. Backup stratejisi oluşturun

---

## 📚 Kaynaklar

- **Hızlı Başlangıç:** [HIZLI_DEPLOYMENT.md](HIZLI_DEPLOYMENT.md)
- **Detaylı Rehber:** [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
- **Veri Yükleme:** [VERI_YUKLEME_REHBERI.md](VERI_YUKLEME_REHBERI.md)

**Başarılar!** 🚀
