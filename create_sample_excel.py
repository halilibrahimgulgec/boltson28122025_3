"""
Test için örnek Excel dosyaları oluştur
"""
import pandas as pd
from datetime import datetime, timedelta
import random

def create_sample_yakit():
    """Örnek yakıt Excel dosyası oluştur"""
    print("📝 Örnek yakıt verileri oluşturuluyor...")

    plakalar = ['34 ABC 123', '35 XYZ 456', '06 DEF 789', '41 GHI 012']
    start_date = datetime(2025, 1, 1)

    data = []
    for i in range(50):  # 50 örnek kayıt
        tarih = start_date + timedelta(days=random.randint(0, 30))
        plaka = random.choice(plakalar)
        yakit_miktari = round(random.uniform(80, 200), 2)
        birim_fiyat = round(random.uniform(38, 45), 2)

        data.append({
            'plaka': plaka,
            'islem_tarihi': tarih.strftime('%Y-%m-%d'),
            'saat': f"{random.randint(8, 18)}:{random.randint(0, 59):02d}",
            'yakit_miktari': yakit_miktari,
            'birim_fiyat': birim_fiyat,
            'satir_tutari': round(yakit_miktari * birim_fiyat, 2),
            'stok_adi': 'Motorin',
            'km_bilgisi': random.randint(100000, 200000)
        })

    df = pd.DataFrame(data)
    filename = 'ornek_yakit.xlsx'
    df.to_excel(filename, index=False)
    print(f"   ✅ {filename} oluşturuldu ({len(data)} kayıt)")
    return filename

def create_sample_agirlik():
    """Örnek ağırlık Excel dosyası oluştur"""
    print("📝 Örnek ağırlık verileri oluşturuluyor...")

    plakalar = ['34 ABC 123', '35 XYZ 456', '06 DEF 789', '41 GHI 012']
    cariler = ['ABC İnşaat', 'XYZ Yapı', 'DEF Madencilik', 'GHI Sanayi']
    adresler = ['İstanbul', 'Ankara', 'İzmir', 'Bursa']
    start_date = datetime(2025, 1, 1)

    data = []
    for i in range(40):  # 40 örnek kayıt
        tarih = start_date + timedelta(days=random.randint(0, 30))
        miktar = round(random.uniform(80, 150), 2)
        net_agirlik = round(miktar * 0.98, 2)  # %2 fire

        data.append({
            'tarih': tarih.strftime('%Y-%m-%d'),
            'miktar': miktar,
            'birim': 'Ton',
            'net_agirlik': net_agirlik,
            'plaka': random.choice(plakalar),
            'adres': random.choice(adresler),
            'islem_noktasi': f'Depo {random.randint(1, 3)}',
            'cari_adi': random.choice(cariler)
        })

    df = pd.DataFrame(data)
    filename = 'ornek_agirlik.xlsx'
    df.to_excel(filename, index=False)
    print(f"   ✅ {filename} oluşturuldu ({len(data)} kayıt)")
    return filename

def create_sample_arac_takip():
    """Örnek araç takip Excel dosyası oluştur"""
    print("📝 Örnek araç takip verileri oluşturuluyor...")

    plakalar = ['34 ABC 123', '35 XYZ 456', '06 DEF 789', '41 GHI 012']
    soforler = ['Ahmet Yılmaz', 'Mehmet Demir', 'Ali Kaya', 'Veli Şahin']
    baslangic_sehirler = ['İstanbul', 'Ankara', 'İzmir']
    bitis_sehirler = ['Bursa', 'Antalya', 'Adana']
    start_date = datetime(2025, 1, 1)

    data = []
    for i in range(30):  # 30 örnek kayıt
        tarih = start_date + timedelta(days=random.randint(0, 30))
        hareket_baslangic = tarih.replace(hour=random.randint(6, 10), minute=0)
        hareket_suresi_saat = random.randint(4, 10)
        hareket_bitis = hareket_baslangic + timedelta(hours=hareket_suresi_saat)

        toplam_km = round(random.uniform(200, 600), 1)
        yakit_tuketimi = round(toplam_km * random.uniform(0.25, 0.35), 1)

        data.append({
            'plaka': random.choice(plakalar),
            'sofor_adi': random.choice(soforler),
            'arac_gruplari': 'Kargo Araçları',
            'tarih': tarih.strftime('%Y-%m-%d'),
            'hareket_baslangic_tarihi': hareket_baslangic.strftime('%Y-%m-%d %H:%M'),
            'hareket_bitis_tarihi': hareket_bitis.strftime('%Y-%m-%d %H:%M'),
            'baslangic_adresi': random.choice(baslangic_sehirler),
            'bitis_adresi': random.choice(bitis_sehirler),
            'toplam_kilometre': toplam_km,
            'hareket_suresi': f"{hareket_suresi_saat}:00:00",
            'rolanti_suresi': f"0:{random.randint(20, 60)}:00",
            'park_suresi': f"{random.randint(1, 4)}:00:00",
            'gunluk_yakit_tuketimi_l': yakit_tuketimi
        })

    df = pd.DataFrame(data)
    filename = 'ornek_arac_takip.xlsx'
    df.to_excel(filename, index=False)
    print(f"   ✅ {filename} oluşturuldu ({len(data)} kayıt)")
    return filename

if __name__ == '__main__':
    print("="*60)
    print("📋 ÖRNEK EXCEL DOSYALARI OLUŞTUR")
    print("="*60)
    print("\n⚠️  Bu script TEST verileri ile örnek Excel dosyaları oluşturur.")
    print("   Gerçek verileriniz varsa bu dosyaları kullanmanıza gerek yok!\n")

    secim = input("Devam etmek istiyor musunuz? (E/H): ").strip().upper()

    if secim == 'E':
        print("\n" + "="*60)
        print("🚀 ÖRNEK DOSYALAR OLUŞTURULUYOR...")
        print("="*60 + "\n")

        files_created = []

        try:
            files_created.append(create_sample_yakit())
        except Exception as e:
            print(f"   ❌ Yakıt dosyası oluşturulamadı: {e}")

        try:
            files_created.append(create_sample_agirlik())
        except Exception as e:
            print(f"   ❌ Ağırlık dosyası oluşturulamadı: {e}")

        try:
            files_created.append(create_sample_arac_takip())
        except Exception as e:
            print(f"   ❌ Araç takip dosyası oluşturulamadı: {e}")

        print("\n" + "="*60)
        print(f"✅ {len(files_created)} dosya oluşturuldu!")
        print("="*60)

        print("\n📤 ŞİMDİ NE YAPMALI?")
        print("1. Oluşturulan Excel dosyalarını kontrol edin")
        print("2. Ardından şu komutu çalıştırın:")
        print("\n   python upload_excel_to_supabase.py\n")
        print("3. Dosya isimlerini şöyle girin:")
        print("   - Yakıt: ornek_yakit")
        print("   - Ağırlık: ornek_agirlik")
        print("   - Araç takip: ornek_arac_takip")
        print("="*60)
    else:
        print("\n❌ İptal edildi.")
