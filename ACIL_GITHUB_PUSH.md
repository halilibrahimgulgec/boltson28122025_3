# 🚨 ACİL: GitHub'a Push Talimatları

## Sorun
Railway, GitHub'daki eski kodu çalıştırıyor. Yeni düzeltmeler GitHub'da yok.

## Düzeltilen Dosyalar
- ✅ `app.py` satır 702: `/binek-arac-analizi` (tire ile)
- ✅ `app.py` satır 775: `/is-makinesi-analizi` (tire ile)

## GitHub'a Nasıl Push Edilir?

### Adım 1: Terminal Aç
Proje klasöründe terminal/cmd aç

### Adım 2: Git Durumunu Kontrol Et
```bash
git status
```

### Adım 3: Değişiklikleri Stage'e Al
```bash
git add app.py
git add templates/binek_arac_filtre.html
git add templates/is_makinesi_filtre.html
```

### Adım 4: Commit Yap
```bash
git commit -m "Fix: Binek ve is makinesi route URL'leri duzeltildi"
```

### Adım 5: GitHub'a Push Et
```bash
git push origin main
```

VEYA (eğer master kullanıyorsan):
```bash
git push origin master
```

## Railway Otomatik Deploy Yapar!
Push yaptıktan 1-2 dakika sonra Railway otomatik olarak yeni kodu deploy eder.

## Kontrol Et
1. Railway Dashboard → "Deployments" → Yeni deploy görünmeli
2. 2 dakika bekle
3. Sayfayı yenile
4. "Binek Araç Analizi" tıkla → Artık çalışacak!

---

## Alternatif: Railway CLI ile Direkt Upload

Eğer git işlemek istemiyorsan:

```bash
npm i -g @railway/cli
railway login
railway link
railway up
```

Bu komutlar GitHub'ı bypass ederek direkt Railway'e upload eder.
