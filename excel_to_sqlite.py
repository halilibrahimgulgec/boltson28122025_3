import pandas as pd
import os
import glob
import hashlib
import sqlite3
from datetime import datetime

# Klasör yolu
klasor = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(klasor, 'kargo_data.db')

# Veritabanı bozuksa sil
if os.path.exists(db_path):
    try:
        test_conn = sqlite3.connect(db_path)
        test_conn.execute('SELECT 1')
        test_conn.close()
    except sqlite3.DatabaseError as e:
        print(f"⚠️  Veritabanı bozuk, yeniden oluşturuluyor...")
        try:
            test_conn.close()
        except:
            pass
        try:
            os.remove(db_path)
        except PermissionError:
            print(f"❌ Veritabanı dosyası kullanımda!")
            print(f"   Çözüm: Flask'ı kapatın (CTRL+C) ve tekrar deneyin")
            exit(1)

# SQLite bağlantısı
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Tabloları oluştur
def create_tables():
    """SQLite tablolarını oluştur"""

    # Yakit tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS yakit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plaka TEXT,
        islem_tarihi TEXT,
        saat TEXT,
        yakit_miktari REAL,
        birim_fiyat REAL,
        satir_tutari REAL,
        stok_adi TEXT,
        km_bilgisi REAL,
        km_fark REAL,
        litre_km REAL,
        toplam_yuk REAL,
        ton_litre REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Agirlik tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agirlik (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        miktar REAL,
        birim TEXT,
        net_agirlik REAL,
        plaka TEXT,
        adres TEXT,
        islem_noktasi TEXT,
        cari_adi TEXT,
        ana_malzeme TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Arac takip tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS arac_takip (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plaka TEXT,
        sofor_adi TEXT,
        arac_gruplari TEXT,
        tarih TEXT,
        hareket_baslangic_tarihi TEXT,
        hareket_bitis_tarihi TEXT,
        baslangic_adresi TEXT,
        bitis_adresi TEXT,
        baslangic_koordinatlari TEXT,
        bitis_koordinatlari TEXT,
        baslangic_kilometre REAL,
        bitis_kilometre REAL,
        maksimum_hiz REAL,
        toplam_kilometre REAL,
        hareket_suresi TEXT,
        rolanti_suresi TEXT,
        park_suresi TEXT,
        toplam_asiri_hiz_alarmi INTEGER,
        toplam_rolanti_alarmi INTEGER,
        gunluk_yakit_tuketimi_l REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # İşlenmiş dosyalar tablosu
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE,
        file_size INTEGER,
        file_hash TEXT,
        record_count INTEGER,
        table_name TEXT,
        processed_at TEXT,
        status TEXT,
        error_message TEXT
    )
    ''')

    conn.commit()
    print("✅ SQLite tabloları oluşturuldu: kargo_data.db\n")


def clear_failed_records():
    """Hatalı işlenmiş dosya kayıtlarını temizle"""
    try:
        cursor.execute("DELETE FROM processed_files WHERE status = 'error'")
        count = cursor.rowcount
        conn.commit()
        if count > 0:
            print(f"🧹 {count} hatalı kayıt temizlendi.\n")
        return count
    except Exception as e:
        print(f"⚠️ Temizleme hatası: {e}")
        return 0


def get_file_hash(file_path):
    """Dosyanın MD5 hash değerini hesapla"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def is_file_processed(filename, file_hash):
    """Dosya daha önce işlendi mi kontrol et"""
    try:
        cursor.execute("SELECT file_hash FROM processed_files WHERE filename = ?", (filename,))
        result = cursor.fetchone()

        if result:
            stored_hash = result[0]
            if stored_hash == file_hash:
                return True, "Aynı dosya daha önce işlendi"
            else:
                return False, "Dosya güncellendi, tekrar işlenecek"
        return False, "Yeni dosya"
    except Exception as e:
        print(f"⚠️ Dosya kontrolü hatası: {e}")
        return False, "Kontrol hatası"


def mark_file_as_processed(filename, file_size, file_hash, record_count, table_name, status="success", error_message=None):
    """Dosyayı işlenmiş olarak işaretle"""
    try:
        processed_at = datetime.now().isoformat()

        # Önce varsa sil
        cursor.execute("DELETE FROM processed_files WHERE filename = ?", (filename,))

        # Yeni ekle
        cursor.execute('''
            INSERT INTO processed_files
            (filename, file_size, file_hash, record_count, table_name, processed_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_size, file_hash, record_count, table_name, processed_at, status, error_message))

        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ Dosya kayıt hatası: {e}")
        return False


def clean_column_name(col_name):
    """Sütun isimlerini temizle"""
    if pd.isna(col_name):
        return "unknown"
    col_name = str(col_name).strip()
    col_name = col_name.replace('\n', ' ').replace('\r', ' ')

    # Türkçe karakterleri dönüştür
    tr_map = {
        'ı': 'i', 'İ': 'i', 'ğ': 'g', 'Ğ': 'g',
        'ü': 'u', 'Ü': 'u', 'ş': 's', 'Ş': 's',
        'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'
    }
    for tr_char, en_char in tr_map.items():
        col_name = col_name.replace(tr_char, en_char)

    col_name = ''.join(c for c in col_name if c.isalnum() or c.isspace() or c == '_')
    return col_name.lower().replace(' ', '_')


def insert_to_sqlite(table_name, data_list):
    """SQLite'a toplu veri ekle"""
    if not data_list:
        return 0

    try:
        # DataFrame'e çevir
        df = pd.DataFrame(data_list)

        # SQLite'a yaz (append mode)
        df.to_sql(table_name, conn, if_exists='append', index=False)

        return len(data_list)
    except Exception as e:
        print(f"❌ SQLite insert hatası ({table_name}): {e}")
        raise


# Tabloları oluştur
create_tables()

# Excel/CSV dosyalarını al
dosyalar_xlsx = [f for f in glob.glob(os.path.join(klasor, "*.xlsx")) if not os.path.basename(f).startswith('~$')]
dosyalar_xls = [f for f in glob.glob(os.path.join(klasor, "*.xls")) if not os.path.basename(f).startswith('~$')]
dosyalar_csv = [f for f in glob.glob(os.path.join(klasor, "*.csv")) if not os.path.basename(f).startswith('~$')]
dosyalar = dosyalar_xlsx + dosyalar_xls + dosyalar_csv
islenen_say = 0
atlanan_say = 0

# Hatalı kayıtları temizle
clear_failed_records()

print(f"📁 Toplam {len(dosyalar)} dosya bulundu (.xlsx, .xls, .csv)\n")

# Ana döngü
for dosya in dosyalar:
    dosya_adi = os.path.basename(dosya)
    dosya_boyutu = os.path.getsize(dosya)
    dosya_hash = get_file_hash(dosya)

    # Dosya daha önce işlendi mi kontrol et
    is_processed, message = is_file_processed(dosya_adi, dosya_hash)

    if is_processed:
        print(f"⏭️  '{dosya_adi}' atlandı → {message}")
        atlanan_say += 1
        continue

    print(f"🔄 '{dosya_adi}' işleniyor...")

    try:
        df = None

        # Dosya türüne göre oku
        if dosya.endswith('.csv'):
            encodings = ['utf-8', 'latin1', 'iso-8859-9', 'cp1254']
            for encoding in encodings:
                try:
                    df = pd.read_csv(dosya, encoding=encoding)
                    break
                except:
                    continue

            if df is None:
                df = pd.read_csv(dosya, encoding='utf-8', errors='ignore')

        elif dosya.endswith(('.xlsx', '.xls')):
            # Excel dosyası - başlık satırını bul
            temp_all = pd.read_excel(dosya, header=None)
            found_header = False

            for idx in range(min(10, len(temp_all))):
                row = temp_all.iloc[idx].astype(str).str.lower()
                if any(keyword in row.values for keyword in ['plaka', 'plate', 'tarih', 'date', 'miktar']):
                    df = pd.read_excel(dosya, skiprows=idx)
                    found_header = True
                    break

            if not found_header:
                df = pd.read_excel(dosya)

        if df is None or df.empty:
            mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, 0, None, "error", "Dosya boş veya okunamadı")
            print(f"❌ '{dosya_adi}' → Veri yok.")
            continue

        # Sütunları temizle
        cols_clean = [clean_column_name(col) for col in df.columns]
        df.columns = cols_clean
        cols = df.columns.tolist()

        # "Toplam" satırını kaldır
        plate_cols = [c for c in cols if 'plaka' in c or 'plate' in c]
        if plate_cols:
            plaka_col = plate_cols[0]
            if plaka_col in df.columns:
                df = df[df[plaka_col].notna()]
                df = df[~df[plaka_col].astype(str).str.contains('toplam|total', case=False, na=True)]

        # --- YAKIT TABLOSU (Motorin Formatı) ---
        if 'plaka' in cols and ('yakit' in cols or 'son_km' in cols or 'km_fark' in cols):
            mapping = {
                'plaka': 'plaka',
                'islem_tarihi': 'islem_tarihi',
                'islem_saat': 'saat',
                'yakit': 'yakit_miktari',
                'son_km': 'km_bilgisi',
                'km_fark': 'km_fark',
                'litre_km': 'litre_km',
                'toplam_yuk': 'toplam_yuk',
                'ton_litre': 'ton_litre'
            }

            selected = [k for k in mapping.keys() if k in cols]
            if len(selected) > 0:
                df_selected = df[selected].copy()
                df_selected.rename(columns=mapping, inplace=True)

                numeric_cols = ['yakit_miktari', 'km_bilgisi', 'km_fark', 'litre_km', 'toplam_yuk', 'ton_litre']
                for col in numeric_cols:
                    if col in df_selected.columns:
                        df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

                if 'islem_tarihi' in df_selected.columns:
                    df_selected['islem_tarihi'] = pd.to_datetime(
                        df_selected['islem_tarihi'], dayfirst=True, errors='coerce'
                    ).dt.strftime('%Y-%m-%d %H:%M:%S')

                # Eksik sütunları None ile doldur
                for col in ['plaka', 'islem_tarihi', 'saat', 'yakit_miktari', 'km_bilgisi', 'km_fark', 'litre_km', 'toplam_yuk', 'ton_litre']:
                    if col not in df_selected.columns:
                        df_selected[col] = None

                records = df_selected.replace([float('nan'), float('inf'), float('-inf')], None).to_dict('records')
                inserted = insert_to_sqlite('yakit', records)
                mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, inserted, 'yakit')

                print(f"⛽ '{dosya_adi}' → {inserted} kayıt 'yakit' tablosuna eklendi.")
                islenen_say += 1

        # --- YAKIT TABLOSU (Eski Format) ---
        elif 'plaka' in cols and ('yakit_miktari' in cols or 'km_bilgisi' in cols):
            mapping = {
                'plaka': 'plaka',
                'islem_tarihi': 'islem_tarihi',
                'saat': 'saat',
                'yakit_miktari': 'yakit_miktari',
                'birim_fiyat': 'birim_fiyat',
                'satir_tutari': 'satir_tutari',
                'stok_adi': 'stok_adi',
                'km_bilgisi': 'km_bilgisi'
            }
            selected = [k for k in mapping.keys() if k in cols]
            df_selected = df[selected].copy()
            df_selected.rename(columns=mapping, inplace=True)

            numeric_cols = ['yakit_miktari', 'birim_fiyat', 'satir_tutari', 'km_bilgisi']
            for col in numeric_cols:
                if col in df_selected.columns:
                    df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

            if 'islem_tarihi' in df_selected.columns:
                df_selected['islem_tarihi'] = pd.to_datetime(
                    df_selected['islem_tarihi'], errors='coerce'
                ).dt.strftime('%Y-%m-%d %H:%M:%S')

            for col in ['plaka', 'islem_tarihi', 'saat', 'yakit_miktari', 'birim_fiyat', 'satir_tutari', 'stok_adi', 'km_bilgisi']:
                if col not in df_selected.columns:
                    df_selected[col] = None

            records = df_selected.replace([float('nan'), float('inf'), float('-inf')], None).to_dict('records')
            inserted = insert_to_sqlite('yakit', records)
            mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, inserted, 'yakit')

            print(f"⛽ '{dosya_adi}' → {inserted} kayıt 'yakit' tablosuna eklendi.")
            islenen_say += 1

        # --- AĞIRLIK TABLOSU ---
        elif any(k in cols for k in ['net_agirlik', 'plaka']) and ('miktar' in cols or 'birim' in cols):
            mapping = {
                'tarih': 'tarih',
                'miktar': 'miktar',
                'birim': 'birim',
                'net_agirlik': 'net_agirlik',
                'plaka': 'plaka',
                'adres': 'adres',
                'islem_noktasi': 'islem_noktasi',
                'cari_adi': 'cari_adi'
            }
            selected = [k for k in mapping.keys() if k in cols]
            df_selected = df[selected].copy()
            df_selected.rename(columns=mapping, inplace=True)

            for col in ['miktar', 'net_agirlik']:
                if col in df_selected.columns:
                    df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')

            if 'tarih' in df_selected.columns:
                df_selected['tarih'] = pd.to_datetime(
                    df_selected['tarih'], format='%d.%m.%Y %H:%M', errors='coerce'
                ).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Ana malzeme hesapla
            # KG=KUM, M3=BETON, M2=PARKE, MT=BORDRO, ADET=PALET (demirbaş, ürün değil)
            if 'birim' in df_selected.columns:
                df_selected['ana_malzeme'] = df_selected['birim'].apply(
                    lambda x: 'KUM' if str(x).upper() == 'KG'
                    else 'BETON' if str(x).upper() == 'M3'
                    else 'PARKE' if str(x).upper() == 'M2'
                    else 'BORDRO' if str(x).upper() == 'MT'
                    else 'PALET' if str(x).upper() == 'ADET'
                    else str(x) if pd.notna(x) else None
                )
            else:
                df_selected['ana_malzeme'] = None

            for col in ['tarih', 'miktar', 'birim', 'net_agirlik', 'plaka', 'adres', 'islem_noktasi', 'cari_adi', 'ana_malzeme']:
                if col not in df_selected.columns:
                    df_selected[col] = None

            records = df_selected.replace([float('nan'), float('inf'), float('-inf')], None).to_dict('records')
            inserted = insert_to_sqlite('agirlik', records)
            mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, inserted, 'agirlik')

            print(f"⚖️  '{dosya_adi}' → {inserted} kayıt 'agirlik' tablosuna eklendi.")
            islenen_say += 1

        # --- ARAÇ TAKİP RAPORU ---
        elif any(k.lower() in ['plaka', 'plate'] for k in cols) and any(k.lower() in ['toplam kilometre', 'sum_distance', 'toplam_kilometre'] for k in cols):
            mapping_raw = {
                'plaka': 'plaka',
                'plate': 'plaka',
                'driver': 'sofor_adi',
                'şoför_adı': 'sofor_adi',
                'sofor_adi': 'sofor_adi',
                'vehicle_groups': 'arac_gruplari',
                'araç_grupları': 'arac_gruplari',
                'arac_gruplari': 'arac_gruplari',
                'tarih': 'tarih',
                'date': 'tarih',
                'hareket_başlangıç_tarihi': 'hareket_baslangic_tarihi',
                'hareket_baslangic_tarihi': 'hareket_baslangic_tarihi',
                'move_start_date': 'hareket_baslangic_tarihi',
                'hareket_bitiş_tarihi': 'hareket_bitis_tarihi',
                'hareket_bitis_tarihi': 'hareket_bitis_tarihi',
                'move_end_date': 'hareket_bitis_tarihi',
                'başlangıç_adresi': 'baslangic_adresi',
                'baslangic_adresi': 'baslangic_adresi',
                'start_address': 'baslangic_adresi',
                'bitiş_adresi': 'bitis_adresi',
                'bitis_adresi': 'bitis_adresi',
                'end_address': 'bitis_adresi',
                'başlangıç_koordinatları': 'baslangic_koordinatlari',
                'baslangic_koordinatlari': 'baslangic_koordinatlari',
                'start_coordinates': 'baslangic_koordinatlari',
                'bitiş_koordinatları': 'bitis_koordinatlari',
                'bitis_koordinatlari': 'bitis_koordinatlari',
                'end_coordinates': 'bitis_koordinatlari',
                'başlangıç_kilometre': 'baslangic_kilometre',
                'baslangic_kilometre': 'baslangic_kilometre',
                'start_km': 'baslangic_kilometre',
                'bitiş_kilometre': 'bitis_kilometre',
                'bitis_kilometre': 'bitis_kilometre',
                'end_km': 'bitis_kilometre',
                'maksimum_hız': 'maksimum_hiz',
                'maksimum_hiz': 'maksimum_hiz',
                'max_speed': 'maksimum_hiz',
                'toplam_kilometre': 'toplam_kilometre',
                'sum_distance': 'toplam_kilometre',
                'hareket_süresi': 'hareket_suresi',
                'hareket_suresi': 'hareket_suresi',
                'move_duration': 'hareket_suresi',
                'rölanti_süresi': 'rolanti_suresi',
                'rolanti_suresi': 'rolanti_suresi',
                'idling_duration': 'rolanti_suresi',
                'park_süresi': 'park_suresi',
                'park_suresi': 'park_suresi',
                'park_duration': 'park_suresi',
                'toplam_rölanti_alarmı': 'toplam_rolanti_alarmi',
                'toplam_rolanti_alarmi': 'toplam_rolanti_alarmi',
                'idling_alarm': 'toplam_rolanti_alarmi',
                'toplam_aşırı_hız_alarmı': 'toplam_asiri_hiz_alarmi',
                'toplam_asiri_hiz_alarmi': 'toplam_asiri_hiz_alarmi',
                'overspeed_alarm': 'toplam_asiri_hiz_alarmi',
                'günlük_yakıt_tüketimi_(l)': 'gunluk_yakit_tuketimi_l',
                'gunluk_yakit_tuketimi_l': 'gunluk_yakit_tuketimi_l',
                'daily_fuel_consumption': 'gunluk_yakit_tuketimi_l'
            }

            selected_cols = {}
            for orig_col in df.columns:
                orig_clean = clean_column_name(orig_col)
                if orig_clean in mapping_raw:
                    selected_cols[orig_col] = mapping_raw[orig_clean]

            if len(selected_cols) < 3:
                mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, 0, None, "error", "Yetersiz sütun eşleşmesi")
                print(f"❌ '{dosya_adi}' → Az sütun eşleşti.")
                continue

            df_selected = df[list(selected_cols.keys())].copy()
            df_selected.rename(columns=selected_cols, inplace=True)

            numeric_cols = [
                'baslangic_kilometre', 'bitis_kilometre', 'maksimum_hiz', 'toplam_kilometre',
                'toplam_asiri_hiz_alarmi', 'toplam_rolanti_alarmi', 'gunluk_yakit_tuketimi_l'
            ]
            for col in numeric_cols:
                if col in df_selected.columns:
                    df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')
                    # Float'ları integer'a çevir (alarm sayıları için)
                    if col in ['toplam_asiri_hiz_alarmi', 'toplam_rolanti_alarmi']:
                        df_selected[col] = df_selected[col].fillna(0).astype('Int64')

            for t_col in ['tarih', 'hareket_baslangic_tarihi', 'hareket_bitis_tarihi']:
                if t_col in df_selected.columns:
                    df_selected[t_col] = pd.to_datetime(
                        df_selected[t_col], dayfirst=True, errors='coerce'
                    ).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Eksik sütunları ekle
            all_cols = [
                'plaka', 'sofor_adi', 'arac_gruplari', 'tarih', 'hareket_baslangic_tarihi',
                'hareket_bitis_tarihi', 'baslangic_adresi', 'bitis_adresi', 'baslangic_koordinatlari',
                'bitis_koordinatlari', 'baslangic_kilometre', 'bitis_kilometre', 'maksimum_hiz',
                'toplam_kilometre', 'hareket_suresi', 'rolanti_suresi', 'park_suresi',
                'toplam_asiri_hiz_alarmi', 'toplam_rolanti_alarmi', 'gunluk_yakit_tuketimi_l'
            ]
            for col in all_cols:
                if col not in df_selected.columns:
                    df_selected[col] = None

            records = df_selected.replace([float('nan'), float('inf'), float('-inf')], None).to_dict('records')
            inserted = insert_to_sqlite('arac_takip', records)
            mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, inserted, 'arac_takip')

            print(f"🚛 '{dosya_adi}' → {inserted} kayıt 'arac_takip' tablosuna eklendi.")
            islenen_say += 1

        else:
            mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, 0, None, "error", "Tablo tipi tanınamadı")
            print(f"❓ '{dosya_adi}' → Tanınamadı.")

    except Exception as e:
        mark_file_as_processed(dosya_adi, dosya_boyutu, dosya_hash, 0, None, "error", str(e))
        print(f"❌ '{dosya_adi}' işlenemedi: {e}")

# Tüm plakaları araclar tablosuna ekle
print(f"\n{'='*60}")
print(f"🚛 Plakaları 'araclar' tablosuna ekleniyor...")

# Önce araclar tablosunu oluştur (yoksa)
cursor.execute('''
CREATE TABLE IF NOT EXISTS araclar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plaka TEXT UNIQUE NOT NULL,
    sahip TEXT NOT NULL CHECK(sahip IN ('BİZİM', 'TAŞERON')),
    arac_tipi TEXT NOT NULL CHECK(arac_tipi IN ('KARGO ARACI', 'İŞ MAKİNESİ', 'DİĞER')),
    aktif INTEGER NOT NULL DEFAULT 1 CHECK(aktif IN (0, 1)),
    notlar TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Tüm unique plakaları topla
all_plakalar = set()

cursor.execute('SELECT DISTINCT plaka FROM yakit WHERE plaka IS NOT NULL')
for row in cursor.fetchall():
    if row[0]:
        all_plakalar.add(row[0])

cursor.execute('SELECT DISTINCT plaka FROM agirlik WHERE plaka IS NOT NULL')
for row in cursor.fetchall():
    if row[0]:
        all_plakalar.add(row[0])

cursor.execute('SELECT DISTINCT plaka FROM arac_takip WHERE plaka IS NOT NULL')
for row in cursor.fetchall():
    if row[0]:
        all_plakalar.add(row[0])

# Her plakayı araclar tablosuna ekle
eklenen_arac = 0
for plaka in all_plakalar:
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO araclar (plaka, sahip, arac_tipi, aktif, notlar)
            VALUES (?, 'BİZİM', 'KARGO ARACI', 1, 'Otomatik eklendi')
        ''', (plaka,))
        if cursor.rowcount > 0:
            eklenen_arac += 1
    except:
        pass

conn.commit()
print(f"✅ {eklenen_arac} plaka 'araclar' tablosuna eklendi.")

# Bağlantıyı kapat
conn.close()

# Özet
print(f"\n{'='*60}")
print(f"🎉 Toplam {islenen_say} yeni dosya işlendi.")
print(f"⏭️  Toplam {atlanan_say} dosya atlandı (daha önce işlendi).")
print(f"{'='*60}")
print(f"\n💾 Veriler SQLite veritabanına kaydedildi!")
print(f"📂 Veritabanı dosyası: {db_path}")
print(f"🔍 DB Browser for SQLite ile açabilirsiniz.")
print(f"\n⚠️  ÖNEMLİ: /arac-yonetimi sayfasından araçları düzenleyip")
print(f"   iş makinelerini ve kullanılmayan araçları ayarlayın!")
