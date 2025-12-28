"""
SQLite veritabanındaki verileri Supabase'e aktarma scripti
"""
import sqlite3
import urllib.request
import json
import os

def load_env():
    """Manuel .env okuma"""
    env_vars = {}
    env_path = '.env'
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
SQLITE_DB = 'kargo_data.db'

def supabase_insert_batch(table, data):
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
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ HTTP Error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def migrate_table(table_name, batch_size=20):
    """Bir tabloyu SQLite'dan Supabase'e aktar"""
    try:
        conn = sqlite3.connect(SQLITE_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()

        if not rows:
            print(f"⚠️  {table_name} tablosu boş")
            return 0

        # Verileri dict listesine çevir
        data = []
        for row in rows:
            row_dict = {}
            for key in row.keys():
                # Supabase'de SERIAL olan id'leri atla (araclar hariç, orada plaka primary key)
                if key == 'id' and table_name != 'araclar':
                    continue

                value = row[key]
                # None değerleri koru, boş string'leri None'a çevir
                if value == '':
                    row_dict[key] = None
                else:
                    row_dict[key] = value
            data.append(row_dict)

        # Batch olarak yükle
        total_uploaded = 0
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            success = supabase_insert_batch(table_name, batch)
            if success:
                total_uploaded += len(batch)
                print(f"✅ {table_name}: {total_uploaded}/{len(data)} kayıt yüklendi")
            else:
                print(f"❌ {table_name}: Batch yükleme başarısız (kayıt {i}-{i+len(batch)})")

        conn.close()
        return total_uploaded

    except Exception as e:
        print(f"❌ {table_name} hatası: {e}")
        return 0

def main():
    print("="*60)
    print("SQLite -> Supabase Veri Aktarımı")
    print("="*60)
    print()

    if not os.path.exists(SQLITE_DB):
        print(f"❌ {SQLITE_DB} dosyası bulunamadı!")
        return

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ .env dosyasında SUPABASE bilgileri eksik!")
        return

    print(f"📊 Kaynak: {SQLITE_DB}")
    print(f"☁️  Hedef: {SUPABASE_URL}")
    print()

    # Tabloları sırayla aktar
    tables = ['yakit', 'agirlik', 'araclar', 'arac_takip']

    for table in tables:
        print(f"\n🔄 {table.upper()} tablosu aktarılıyor...")
        uploaded = migrate_table(table)
        print(f"✅ {table}: {uploaded} kayıt aktarıldı")

    print()
    print("="*60)
    print("✅ Veri aktarımı tamamlandı!")
    print("="*60)
    print()
    print("Şimdi uygulamayı yeniden başlatın: python app.py")

if __name__ == '__main__':
    main()
