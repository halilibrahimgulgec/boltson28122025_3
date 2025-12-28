# 🚛 Kargo Yakıt Analiz Sistemi

Supabase veritabanı tabanlı kapsamlı yakıt tüketimi analiz, tahmin ve araç yönetim sistemi.

## ⚡ Özellikler

- 🔍 **Kargo Araçları Analizi** - Detaylı tonaj ve yakıt tüketimi analizi
- 🚗 **Binek Araç Analizi** - Yakıt performansı ve maliyet takibi
- 🚜 **İş Makinesi Analizi** - Operasyon verimliliği ölçümü
- 📊 **Tarih & Plaka Filtreleme** - Her sayfada özelleştirilmiş filtreler
- 🚛 **Araç Yönetimi** - Araç envanteri ve kategorizasyon
- 🤖 **AI Analiz** - Yapay zeka destekli yakıt tahminleri
- 🤖 **AI Asistan** - Ollama LLM ile sorularınızı yanıtlar
- 💰 **Muhasebe Analizi** - Maliyet ve bütçe takibi
- 📈 **Grafik Gösterimi** - Chart.js ile interaktif görselleştirmeler
- 📤 **Veri Yükleme** - Web arayüzünden Excel dosyası yükleme
- 💾 **Excel/PDF Export** - Raporları dışa aktarma
- 🔍 **Veritabanı Durumu** - Anlık durum kontrolü

## 🚀 Kurulum

### 1. Repository'yi Klonlayın

```bash
git clone <repository-url>
cd project
```

### 2. Python Bağımlılıklarını Yükleyin

```bash
pip install -r requirements.txt
```

### 3. Environment Değişkenlerini Ayarlayın

`.env.example` dosyasını `.env` olarak kopyalayın ve Supabase bilgilerinizi girin:

```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin:

```env
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
```

### 4. Uygulamayı Başlatın

```bash
python app.py
```

Tarayıcınızda şu adresi açın: `http://localhost:5000`

## 📁 Proje Yapısı

```
project/
├── app.py                      # Ana Flask uygulaması
├── database.py                 # Supabase veritabanı işlemleri
├── model_analyzer.py           # Veri analiz modülü
├── ai_model.py                 # AI tahmin modelleri
├── ollama_assistant.py         # Ollama AI Asistan
├── requirements.txt            # Python bağımlılıkları
├── .env                        # Environment değişkenleri (Supabase)
├── .env.example                # Environment şablonu
└── templates/                  # HTML şablonları
    ├── index.html              # Ana sayfa
    ├── kargo_arac_filtre.html  # Kargo araçları analizi
    ├── binek_arac_filtre.html  # Binek araç analizi
    ├── is_makinesi_filtre.html # İş makinesi analizi
    ├── arac_yonetimi.html      # Araç yönetimi
    ├── ai_analysis.html        # AI analiz sayfası
    ├── ai_assistant.html       # AI asistan
    ├── muhasebe.html           # Muhasebe analizi
    └── veri_yukleme.html       # Veri yükleme sayfası
```

## 🗄️ Veritabanı Yapısı (Supabase)

### Tablolar

**yakit** - Yakıt kayıtları
- plaka, islem_tarihi, yakit_miktari, birim_fiyat, satir_tutari, km_bilgisi

**agirlik** - Kantar kayıtları
- plaka, tarih, miktar, net_agirlik, cari_adi

**arac_takip** - GPS takip kayıtları
- plaka, tarih, toplam_kilometre, hareket_suresi, gunluk_yakit_tuketimi_l

**araclar** - Araç envanteri
- plaka, sahiplik, kategori, marka, model, yil

## 🎯 Kullanım

### Ana Sayfa (/)
- Veritabanı durum özeti
- Hızlı erişim butonları
- Plaka listesi

### Kargo Araçları Analizi (/kargo_arac_filtre)
- Tarih ve plaka bazlı filtreleme
- Tonaj analizi
- Yakıt tüketimi grafiği

### Binek Araç Analizi (/binek_arac_filtre)
- Yakıt performansı
- Kilometre bazlı analiz

### İş Makinesi Analizi (/is_makinesi_filtre)
- Operasyon verimliliği
- Çalışma süresi analizi

### Araç Yönetimi (/arac_yonetimi)
- Araç ekleme/düzenleme/silme
- Kategori yönetimi
- Performans karşılaştırma

### AI Analiz (/ai_analysis)
- Yakıt tüketim tahmini
- Anomali tespiti
- Toplu tahmin

### AI Asistan (/ai_assistant)
- Ollama LLM ile sohbet
- Veritabanı sorguları
- Doğal dil işleme

### Muhasebe (/muhasebe)
- Maliyet analizi
- Bütçe takibi
- Excel/PDF export

### Veri Yükleme (/veri_yukleme)
- Excel dosyası yükleme
- Otomatik veri aktarımı
- Format doğrulama

## 📊 API Endpoints

- `GET /` - Ana sayfa
- `GET /kargo_arac_filtre` - Kargo araç filtresi
- `GET /binek_arac_filtre` - Binek araç filtresi
- `GET /is_makinesi_filtre` - İş makinesi filtresi
- `GET /arac_yonetimi` - Araç yönetimi
- `GET /ai_analysis` - AI analiz
- `GET /ai_assistant` - AI asistan
- `GET /muhasebe` - Muhasebe
- `GET /veri_yukleme` - Veri yükleme
- `POST /muhasebe/rapor` - Muhasebe raporu
- `POST /muhasebe/export_pdf` - PDF export

## 🤖 Ollama AI Asistan Kurulumu

1. Ollama'yı yükleyin: https://ollama.ai
2. Bir model çekin:
```bash
ollama pull llama2
```
3. Test edin:
```bash
python test_ollama.py
```

Detaylı kurulum için: [OLLAMA_KURULUM.md](OLLAMA_KURULUM.md)

## 🔧 Sorun Giderme

### Port 5000 Kullanımda
`app.py` dosyasında portu değiştirin:
```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Supabase Bağlantı Hatası
- `.env` dosyasındaki bilgileri kontrol edin
- Supabase dashboard'dan API anahtarlarını doğrulayın

### AI Özellikleri Çalışmıyor
- Ollama'nın yüklü ve çalışır durumda olduğunu kontrol edin
- `http://localhost:11434` adresinin erişilebilir olduğunu doğrulayın

## 🔒 Güvenlik

- `.env` dosyası `.gitignore` içinde (GitHub'a yüklenmez)
- Supabase Row Level Security (RLS) politikaları
- API anahtarları environment değişkenlerinde saklanır
- Secret key değiştirilebilir (`app.py`)

## 📄 Lisans

Bu proje kargo şirketi için özel olarak geliştirilmiştir.

---

**Son Güncelleme:** 02 Aralık 2025
**Versiyon:** 3.0 (Supabase + Route Fix)
