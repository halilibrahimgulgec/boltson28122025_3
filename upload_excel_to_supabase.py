"""
Excel dosyalarını Supabase'e yükle - DOĞRU VERSİYON
- Eski verileri SİLMEZ
- Sadece YENİ kayıtları ekler
- Birden fazla dosya yükleyebilir
"""
import pandas as pd
import urllib.request
import json
import os
from datetime import datetime
import hashlib

# .env dosyasını manuel oku
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

env = load_env()
SUPABASE_URL = env.get('VITE_SUPABASE_URL')
SUPABASE_KEY = env.get('VITE_SUPABASE_ANON_KEY')

def create_record_hash(record: dict) -> str:
    """Kayıt için benzersiz hash oluştur (duplicate kontrolü için)"""
    # Önemli alanları birleştir ve hash'le
    key_parts = []
    for key in sorted(record.keys()):
        if record[key] is not None:
            key_parts.append(f"{key}:{record[key]}")
    hash_string = '|'.join(key_parts)
    return hashlib.md5(hash_string.encode()).hexdigest()

def supabase_insert_batch(table: str, data: list):
    """Supabase'e toplu veri ekle"""
    if not data:
        return True

    url = f'{SUPABASE_URL}/rest/v1/{table}'

    req = urllib.request.Request(url, method='POST')
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=minimal')

    req.data = json.dumps(data).encode()

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 201
    except Exception as e:
        print(f"   ❌ Hata: {e}")
        return False

def get_existing_hashes(table: str) -> set:
    """Tablodaki mevcut kayıtların hash'lerini al"""
    try:
        url = f'{SUPABASE_URL}/rest/v1/{table}?select=record_hash'

        req = urllib.request.Request(url, method='GET')
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {row.get('record_hash') for row in data if row.get('record_hash')}
    except:
        return set()

def upload_yakit(excel_file):
    """Yakıt Excel dosyasını yükle"""
    print(f"\n⛽ Yakıt dosyası: {excel_file}")

    try:
        if excel_file.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd')
        else:
            df = pd.read_excel(excel_file)
        print(f"   📊 {len(df)} satır okundu")

        # Kolon isimlerini düzelt
        df.columns = df.columns.str.strip().str.lower()

        # Mevcut hash'leri al (duplicate kontrolü için)
        existing_hashes = get_existing_hashes('yakit')

        # Verileri hazırla
        records = []
        skipped = 0

        for _, row in df.iterrows():
            record = {
                'plaka': str(row.get('plaka', '')).strip() if pd.notna(row.get('plaka')) else None,
                'islem_tarihi': str(row.get('islem_tarihi', '')) if pd.notna(row.get('islem_tarihi')) else None,
                'saat': str(row.get('saat', '')) if pd.notna(row.get('saat')) else None,
                'yakit_miktari': float(row.get('yakit_miktari', 0)) if pd.notna(row.get('yakit_miktari')) else None,
                'birim_fiyat': float(row.get('birim_fiyat', 0)) if pd.notna(row.get('birim_fiyat')) else None,
                'satir_tutari': float(row.get('satir_tutari', 0)) if pd.notna(row.get('satir_tutari')) else None,
                'stok_adi': str(row.get('stok_adi', '')) if pd.notna(row.get('stok_adi')) else None,
                'km_bilgisi': float(row.get('km_bilgisi', 0)) if pd.notna(row.get('km_bilgisi')) else None
            }

            # Hash oluştur ve kontrol et
            record_hash = create_record_hash(record)

            if record_hash in existing_hashes:
                skipped += 1
                continue

            record['record_hash'] = record_hash
            records.append(record)

        if not records:
            print(f"   ℹ️  Yeni kayıt yok - {skipped} kayıt zaten veritabanında mevcut (atlandı)")
            print(f"   ✅ Tekrarlı veri engellendi!")
            return True

        # Batch olarak yükle
        batch_size = 1000
        success = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            if supabase_insert_batch('yakit', batch):
                success += len(batch)
                print(f"   ✅ {success}/{len(records)} yeni kayıt eklendi")

        if skipped > 0:
            print(f"   ℹ️  {skipped} kayıt atlandı (zaten mevcut)")

        print(f"   ✅ Toplam: {success} YENİ kayıt eklendi")
        return True

    except Exception as e:
        print(f"   ❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

def upload_agirlik(excel_file):
    """Ağırlık Excel dosyasını yükle"""
    print(f"\n⚖️  Ağırlık dosyası: {excel_file}")

    try:
        if excel_file.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd')
        else:
            df = pd.read_excel(excel_file)
        print(f"   📊 {len(df)} satır okundu")

        df.columns = df.columns.str.strip().str.lower()
        existing_hashes = get_existing_hashes('agirlik')

        records = []
        skipped = 0

        for _, row in df.iterrows():
            record = {
                'tarih': str(row.get('tarih', '')) if pd.notna(row.get('tarih')) else None,
                'miktar': float(row.get('miktar', 0)) if pd.notna(row.get('miktar')) else None,
                'birim': str(row.get('birim', '')) if pd.notna(row.get('birim')) else None,
                'net_agirlik': float(row.get('net_agirlik', 0)) if pd.notna(row.get('net_agirlik')) else None,
                'plaka': str(row.get('plaka', '')).strip() if pd.notna(row.get('plaka')) else None,
                'adres': str(row.get('adres', '')) if pd.notna(row.get('adres')) else None,
                'islem_noktasi': str(row.get('islem_noktasi', '')) if pd.notna(row.get('islem_noktasi')) else None,
                'cari_adi': str(row.get('cari_adi', '')) if pd.notna(row.get('cari_adi')) else None
            }

            record_hash = create_record_hash(record)
            if record_hash in existing_hashes:
                skipped += 1
                continue

            record['record_hash'] = record_hash
            records.append(record)

        if not records:
            print(f"   ℹ️  Yeni kayıt yok - {skipped} kayıt zaten veritabanında mevcut (atlandı)")
            print(f"   ✅ Tekrarlı veri engellendi!")
            return True

        batch_size = 1000
        success = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            if supabase_insert_batch('agirlik', batch):
                success += len(batch)
                print(f"   ✅ {success}/{len(records)} yeni kayıt eklendi")

        if skipped > 0:
            print(f"   ℹ️  {skipped} kayıt atlandı")

        print(f"   ✅ Toplam: {success} YENİ kayıt eklendi")
        return True

    except Exception as e:
        print(f"   ❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

def upload_arac_takip(excel_file):
    """Araç takip Excel dosyasını yükle"""
    print(f"\n🚛 Araç takip dosyası: {excel_file}")

    try:
        if excel_file.endswith('.xls'):
            df = pd.read_excel(excel_file, engine='xlrd')
        else:
            df = pd.read_excel(excel_file)
        print(f"   📊 {len(df)} satır okundu")

        df.columns = df.columns.str.strip().str.lower()
        existing_hashes = get_existing_hashes('arac_takip')

        records = []
        skipped = 0

        for _, row in df.iterrows():
            record = {
                'plaka': str(row.get('plaka', '')).strip() if pd.notna(row.get('plaka')) else None,
                'sofor_adi': str(row.get('sofor_adi', '')) if pd.notna(row.get('sofor_adi')) else None,
                'arac_gruplari': str(row.get('arac_gruplari', '')) if pd.notna(row.get('arac_gruplari')) else None,
                'tarih': str(row.get('tarih', '')) if pd.notna(row.get('tarih')) else None,
                'hareket_baslangic_tarihi': str(row.get('hareket_baslangic_tarihi', '')) if pd.notna(row.get('hareket_baslangic_tarihi')) else None,
                'hareket_bitis_tarihi': str(row.get('hareket_bitis_tarihi', '')) if pd.notna(row.get('hareket_bitis_tarihi')) else None,
                'baslangic_adresi': str(row.get('baslangic_adresi', '')) if pd.notna(row.get('baslangic_adresi')) else None,
                'bitis_adresi': str(row.get('bitis_adresi', '')) if pd.notna(row.get('bitis_adresi')) else None,
                'toplam_kilometre': float(row.get('toplam_kilometre', 0)) if pd.notna(row.get('toplam_kilometre')) else None,
                'hareket_suresi': str(row.get('hareket_suresi', '')) if pd.notna(row.get('hareket_suresi')) else None,
                'rolanti_suresi': str(row.get('rolanti_suresi', '')) if pd.notna(row.get('rolanti_suresi')) else None,
                'park_suresi': str(row.get('park_suresi', '')) if pd.notna(row.get('park_suresi')) else None,
                'gunluk_yakit_tuketimi_l': float(row.get('gunluk_yakit_tuketimi_l', 0)) if pd.notna(row.get('gunluk_yakit_tuketimi_l')) else None
            }

            record_hash = create_record_hash(record)
            if record_hash in existing_hashes:
                skipped += 1
                continue

            record['record_hash'] = record_hash
            records.append(record)

        if not records:
            print(f"   ℹ️  Yeni kayıt yok - {skipped} kayıt zaten veritabanında mevcut (atlandı)")
            print(f"   ✅ Tekrarlı veri engellendi!")
            return True

        batch_size = 1000
        success = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            if supabase_insert_batch('arac_takip', batch):
                success += len(batch)
                print(f"   ✅ {success}/{len(records)} yeni kayıt eklendi")

        if skipped > 0:
            print(f"   ℹ️  {skipped} kayıt atlandı")

        print(f"   ✅ Toplam: {success} YENİ kayıt eklendi")
        return True

    except Exception as e:
        print(f"   ❌ Hata: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_excel_files():
    """Klasördeki tüm Excel dosyalarını bul"""
    excel_files = {}

    for file in os.listdir('.'):
        if file.endswith(('.xlsx', '.xls')):
            lower_name = file.lower()

            # Dosya tipini tahmin et
            if 'yakit' in lower_name or 'beton' in lower_name or 'motorin' in lower_name:
                excel_files.setdefault('yakit', []).append(file)
            elif 'agirlik' in lower_name or 'kantar' in lower_name:
                excel_files.setdefault('agirlik', []).append(file)
            elif 'takip' in lower_name or 'arac' in lower_name:
                excel_files.setdefault('arac_takip', []).append(file)
            else:
                excel_files.setdefault('unknown', []).append(file)

    return excel_files

if __name__ == '__main__':
    print("="*70)
    print("📤 EXCEL DOSYALARINI SUPABASE'E YÜKLE (YENİ KAYITLAR)")
    print("="*70)
    print("\n⚠️  ÖNEMLİ:")
    print("   • Eski veriler SİLİNMEZ")
    print("   • Sadece YENİ kayıtlar eklenir")
    print("   • Aynı kayıt tekrar eklenmez (duplicate kontrol)")
    print("   • Her gün yeni dosyalar yükleyebilirsiniz")
    print("="*70)

    # Otomatik dosya tespiti
    excel_files = find_excel_files()

    if not any(excel_files.values()):
        print("\n❌ Bu klasörde Excel dosyası bulunamadı!")
        print("   Excel dosyalarınızı bu klasöre koyun ve tekrar deneyin.")
        input("\nÇıkmak için Enter'a basın...")
        exit(1)

    print("\n📁 Bulunan Excel dosyaları:")
    for file_type, files in excel_files.items():
        if files:
            type_name = {
                'yakit': '⛽ Yakıt',
                'agirlik': '⚖️  Ağırlık',
                'arac_takip': '🚛 Araç Takip',
                'unknown': '❓ Belirsiz'
            }.get(file_type, file_type)

            print(f"\n{type_name}:")
            for f in files:
                print(f"   • {f}")

    print("\n" + "="*70)
    choice = input("Bu dosyaları yüklemek istiyor musunuz? (E/H): ").strip().upper()

    if choice != 'E':
        print("\n❌ İptal edildi.")
        exit(0)

    print("\n" + "="*70)
    print("🚀 YÜKLEME BAŞLIYOR...")
    print("="*70)

    success_count = 0
    total_count = 0

    # Yakıt dosyalarını yükle
    if 'yakit' in excel_files:
        for file in excel_files['yakit']:
            total_count += 1
            if upload_yakit(file):
                success_count += 1

    # Ağırlık dosyalarını yükle
    if 'agirlik' in excel_files:
        for file in excel_files['agirlik']:
            total_count += 1
            if upload_agirlik(file):
                success_count += 1

    # Araç takip dosyalarını yükle
    if 'arac_takip' in excel_files:
        for file in excel_files['arac_takip']:
            total_count += 1
            if upload_arac_takip(file):
                success_count += 1

    # Belirsiz dosyalar için kullanıcıya sor
    if 'unknown' in excel_files and excel_files['unknown']:
        print("\n" + "="*70)
        print("❓ Belirsiz dosyalar bulundu:")
        for f in excel_files['unknown']:
            print(f"   • {f}")
        print("\nBu dosyalar hangi tipe ait?")
        print("1. Yakıt")
        print("2. Ağırlık")
        print("3. Araç Takip")
        print("4. Atla")

        for file in excel_files['unknown']:
            choice = input(f"\n'{file}' için seçim (1-4): ").strip()
            total_count += 1

            if choice == '1' and upload_yakit(file):
                success_count += 1
            elif choice == '2' and upload_agirlik(file):
                success_count += 1
            elif choice == '3' and upload_arac_takip(file):
                success_count += 1

    print("\n" + "="*70)
    print(f"✅ TAMAMLANDI: {success_count}/{total_count} dosya başarıyla yüklendi")
    print("="*70)
    print("\n🎯 SONRAKİ ADIMLAR:")
    print("   1. Flask uygulamasını başlatın: python app.py")
    print("   2. Tarayıcıda açın: http://localhost:5000")
    print("   3. Yeni veriler her gün eklenebilir!")
    print("="*70)
