"""
SQLite veritabanı şeması oluşturma scripti
"""
import sqlite3
import os

DB_PATH = 'kargo_data.db'

def init_database():
    """Veritabanı tablolarını oluştur"""
    print(f"📦 Veritabanı başlatılıyor: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Yakıt Tablosu (Supabase uyumlu)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS yakit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plaka TEXT,
            islem_tarihi DATE,
            saat TEXT,
            yakit_miktari REAL,
            birim_fiyat REAL,
            satir_tutari REAL,
            stok_adi TEXT,
            km_bilgisi REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            km_fark REAL,
            litre_km REAL,
            toplam_yuk REAL,
            ton_litre REAL,
            record_hash TEXT
        )
    ''')
    print("✓ yakit tablosu oluşturuldu")

    # 2. Ağırlık Tablosu (Supabase uyumlu)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih DATE,
            miktar REAL,
            birim TEXT,
            net_agirlik REAL,
            plaka TEXT,
            adres TEXT,
            islem_noktasi TEXT,
            cari_adi TEXT,
            ana_malzeme TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_hash TEXT
        )
    ''')
    print("✓ agirlik tablosu oluşturuldu")

    # 3. Araçlar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS araclar (
            plaka TEXT PRIMARY KEY,
            sahip TEXT DEFAULT 'BİZİM',
            arac_tipi TEXT DEFAULT 'KARGO ARACI',
            aktif INTEGER DEFAULT 1,
            notlar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ araclar tablosu oluşturuldu")

    # 4. Araç Takip Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arac_takip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plaka TEXT,
            tarih DATE,
            konum TEXT,
            durum TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ arac_takip tablosu oluşturuldu")

    # 5. İşlenen Dosyalar Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            table_name TEXT,
            record_count INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ processed_files tablosu oluşturuldu")

    # İndeksler
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_yakit_plaka ON yakit(plaka)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_yakit_tarih ON yakit(islem_tarihi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agirlik_plaka ON agirlik(plaka)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agirlik_tarih ON agirlik(tarih)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_araclar_tipi ON araclar(arac_tipi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_araclar_aktif ON araclar(aktif)')
    print("✓ İndeksler oluşturuldu")

    # Demo veri ekle
    demo_plakalar = [
        ('34ABC123', 'BİZİM', 'KARGO ARACI', 1, 'Demo kargo aracı'),
        ('06XYZ789', 'BİZİM', 'BİNEK ARAÇ', 1, 'Demo binek araç'),
        ('34DEF456', 'BİZİM', 'İŞ MAKİNESİ', 1, 'Demo iş makinesi'),
    ]

    cursor.executemany('''
        INSERT OR IGNORE INTO araclar (plaka, sahip, arac_tipi, aktif, notlar)
        VALUES (?, ?, ?, ?, ?)
    ''', demo_plakalar)

    print(f"✓ {len(demo_plakalar)} demo araç eklendi")

    conn.commit()
    conn.close()

    print("\n✅ Veritabanı başarıyla oluşturuldu!")
    print(f"📍 Konum: {os.path.abspath(DB_PATH)}")
    print("\n💡 Şimdi Excel dosyalarınızı 'Veri Yükleme' sayfasından yükleyebilirsiniz.")

if __name__ == '__main__':
    init_database()
