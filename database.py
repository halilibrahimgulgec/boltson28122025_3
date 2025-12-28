"""
Supabase veritabanı işlemleri
"""
import os
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.parse
import json

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

# Railway environment variables'ı önce dene, yoksa .env'den al
env = load_env()
SUPABASE_URL = (
    os.environ.get('VITE_SUPABASE_URL') or
    os.environ.get('SUPABASE_URL') or
    env.get('VITE_SUPABASE_URL') or
    env.get('SUPABASE_URL')
)
SUPABASE_KEY = (
    os.environ.get('VITE_SUPABASE_ANON_KEY') or
    os.environ.get('SUPABASE_ANAHTAR') or
    env.get('VITE_SUPABASE_ANON_KEY') or
    env.get('SUPABASE_ANAHTAR')
)

# Supabase credentials kontrolü
import logging
logger = logging.getLogger(__name__)

if not SUPABASE_URL or not SUPABASE_KEY:
    error_msg = "❌ KRİTİK HATA: Supabase credentials bulunamadı!\n"
    error_msg += f"SUPABASE_URL: {'✓ OK' if SUPABASE_URL else '✗ EKSİK'}\n"
    error_msg += f"SUPABASE_KEY: {'✓ OK' if SUPABASE_KEY else '✗ EKSİK'}\n"
    error_msg += "\nRailway Variables sekmesine şunları ekleyin:\n"
    error_msg += "- VITE_SUPABASE_URL\n"
    error_msg += "- VITE_SUPABASE_ANON_KEY\n"
    logger.error(error_msg)
    print(error_msg)
else:
    logger.info(f"✓ Supabase bağlantısı OK: {SUPABASE_URL[:30]}...")

def supabase_insert_batch(table: str, data: list):
    """Supabase'e toplu veri ekle"""
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
        print(f"❌ Batch insert error: {e}")
        return False

def record_processed_file(filename: str, table_name: str, record_count: int):
    """İşlenen dosyayı kaydet"""
    try:
        data = {
            'filename': filename,
            'table_name': table_name,
            'record_count': record_count,
            'status': 'success'
        }
        supabase_insert_batch('processed_files', [data])
    except:
        pass

def supabase_request(endpoint: str, method: str = 'GET', data: dict = None, params: dict = None):
    """Supabase REST API isteği"""
    url = f'{SUPABASE_URL}/rest/v1/{endpoint}'

    if params:
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        url = f'{url}?{query_string}'

    req = urllib.request.Request(url, method=method)
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')

    if data:
        req.data = json.dumps(data).encode()

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise Exception(f"Supabase error: {e.code} - {error_body}")

def fetch_all_paginated(table: str, select: str = '*', filters: dict = None, order: str = None):
    """Tüm verileri pagination ile çek"""
    all_data = []
    offset = 0
    limit = 1000

    while True:
        url = f'{SUPABASE_URL}/rest/v1/{table}?select={urllib.parse.quote(select)}&limit={limit}&offset={offset}'

        if filters:
            for key, value in filters.items():
                encoded_value = urllib.parse.quote(str(value))
                url += f'&{key}={encoded_value}'

        if order:
            url += f'&order={urllib.parse.quote(order)}'

        req = urllib.request.Request(url)
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req) as response:
                batch = json.loads(response.read().decode())
                if not batch or len(batch) == 0:
                    break
                all_data.extend(batch)

                if len(batch) < limit:
                    break
                offset += limit
        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    return all_data

def hesapla_gercek_km(plaka: str, baslangic_tarihi: str = None, bitis_tarihi: str = None) -> float:
    """
    Bir aracın gerçek gidilen kilometresini hesapla

    Args:
        plaka: Araç plakası
        baslangic_tarihi: Başlangıç tarihi (YYYY-MM-DD)
        bitis_tarihi: Bitiş tarihi (YYYY-MM-DD)

    Returns:
        float: Toplam gidilen kilometre
    """
    try:
        url = f'{SUPABASE_URL}/rest/v1/yakit?plaka=eq.{urllib.parse.quote(plaka)}&km_bilgisi=not.is.null&order=islem_tarihi.asc'

        if baslangic_tarihi and bitis_tarihi:
            url += f'&islem_tarihi=and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            url += f'&islem_tarihi=gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            url += f'&islem_tarihi=lte.{bitis_tarihi}'

        req = urllib.request.Request(url)
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')

        with urllib.request.urlopen(req) as response:
            rows = json.loads(response.read().decode())

        if len(rows) < 2:
            return 0

        toplam_km = 0
        onceki_km = None

        for row in rows:
            km = float(row['km_bilgisi']) if row.get('km_bilgisi') else 0

            if km > 0 and onceki_km is not None:
                fark = km - onceki_km
                if fark > 0:
                    toplam_km += fark

            if km > 0:
                onceki_km = km

        return toplam_km
    except Exception as e:
        print(f"Error calculating km: {e}")
        return 0

def get_database_info() -> Dict[str, Any]:
    """Veritabanı bilgilerini getir"""
    try:
        yakit_count = 0
        agirlik_count = 0
        arac_takip_count = 0

        try:
            yakit_count = len(fetch_all_paginated('yakit', select='id'))
        except:
            pass

        try:
            agirlik_count = len(fetch_all_paginated('agirlik', select='id'))
        except:
            pass

        try:
            arac_takip_count = len(fetch_all_paginated('arac_takip', select='id'))
        except:
            pass

        total = yakit_count + agirlik_count + arac_takip_count

        return {
            'exists': total > 0,
            'yakit_count': yakit_count,
            'agirlik_count': agirlik_count,
            'arac_takip_count': arac_takip_count,
            'total_records': total
        }
    except Exception as e:
        print(f"⚠️ get_database_info hatası: {e}")
        return {
            'exists': False,
            'yakit_count': 0,
            'agirlik_count': 0,
            'arac_takip_count': 0,
            'total_records': 0,
            'error': str(e)
        }

def get_statistics() -> Dict[str, Any]:
    """İstatistikleri getir"""
    try:
        # Tablolar boşsa bile hata vermemesi için güvenli veri çekimi
        yakit_data = []
        agirlik_data = []
        arac_takip_data = []

        try:
            yakit_data = fetch_all_paginated('yakit', select='yakit_miktari,satir_tutari,plaka')
        except:
            pass

        try:
            agirlik_data = fetch_all_paginated('agirlik', select='id')
        except:
            pass

        try:
            arac_takip_data = fetch_all_paginated('arac_takip', select='id')
        except:
            pass

        toplam_yakit = sum(float(row.get('yakit_miktari', 0) or 0) for row in yakit_data if row.get('yakit_miktari'))
        toplam_maliyet = sum(float(row.get('satir_tutari', 0) or 0) for row in yakit_data if row.get('satir_tutari'))
        plakalar = list(set(row['plaka'] for row in yakit_data if row.get('plaka')))

        return {
            'toplam_yakit': round(toplam_yakit, 2),
            'toplam_maliyet': round(toplam_maliyet, 2),
            'plaka_sayisi': len(plakalar),
            'plakalar': sorted(plakalar) if plakalar else [],
            'yakit_kayit': len(yakit_data),
            'agirlik_kayit': len(agirlik_data),
            'arac_takip_kayit': len(arac_takip_data),
            'toplam_kayit': len(yakit_data) + len(agirlik_data) + len(arac_takip_data)
        }
    except Exception as e:
        print(f"⚠️ get_statistics hatası: {e}")
        return {
            'toplam_yakit': 0,
            'toplam_maliyet': 0,
            'plaka_sayisi': 0,
            'plakalar': [],
            'yakit_kayit': 0,
            'agirlik_kayit': 0,
            'arac_takip_kayit': 0,
            'toplam_kayit': 0
        }

def get_aktif_kargo_araclari() -> List[str]:
    """Aktif kargo araçlarını getir"""
    try:
        data = fetch_all_paginated('araclar',
                                   select='plaka',
                                   filters={'arac_tipi': 'eq.KARGO ARACI', 'aktif': 'eq.1', 'sahip': 'eq.BİZİM'})
        plakalar = [row['plaka'] for row in data]

        # Eğer araclar tablosu boşsa, yakit tablosundaki tüm plakaları kullan
        if not plakalar:
            print("⚠️ araclar tablosu boş, yakit tablosundaki plakalar kullanılıyor...")
            yakit_data = fetch_all_paginated('yakit', select='plaka')
            plakalar = sorted(list(set(row['plaka'] for row in yakit_data if row.get('plaka'))))

        return plakalar
    except Exception as e:
        print(f"⚠️ get_aktif_kargo_araclari hatası: {e}")
        return []

def get_aktif_binek_araclar(dahil_taseron: bool = False) -> List[str]:
    """Aktif binek araçları getir"""
    try:
        filters = {'arac_tipi': 'eq.BİNEK ARAÇ', 'aktif': 'eq.1'}
        if not dahil_taseron:
            filters['sahip'] = 'eq.BİZİM'

        data = fetch_all_paginated('araclar', select='plaka', filters=filters)
        plakalar = [row['plaka'] for row in data]

        # Eğer araclar tablosu boşsa, yakit tablosundaki tüm plakaları kullan
        if not plakalar:
            print("⚠️ araclar tablosu boş, yakit tablosundaki plakalar kullanılıyor...")
            yakit_data = fetch_all_paginated('yakit', select='plaka')
            plakalar = sorted(list(set(row['plaka'] for row in yakit_data if row.get('plaka'))))

        return plakalar
    except Exception as e:
        print(f"⚠️ get_aktif_binek_araclar hatası: {e}")
        return []

def get_aktif_is_makineleri(dahil_taseron: bool = False) -> List[str]:
    """Aktif iş makinelerini getir"""
    try:
        filters = {'arac_tipi': 'eq.İŞ MAKİNESİ', 'aktif': 'eq.1'}
        if not dahil_taseron:
            filters['sahip'] = 'eq.BİZİM'

        data = fetch_all_paginated('araclar', select='plaka', filters=filters)
        plakalar = [row['plaka'] for row in data]

        # Eğer araclar tablosu boşsa, yakit tablosundaki tüm plakaları kullan
        if not plakalar:
            print("⚠️ araclar tablosu boş, yakit tablosundaki plakalar kullanılıyor...")
            yakit_data = fetch_all_paginated('yakit', select='plaka')
            plakalar = sorted(list(set(row['plaka'] for row in yakit_data if row.get('plaka'))))

        return plakalar
    except Exception as e:
        print(f"⚠️ get_aktif_is_makineleri hatası: {e}")
        return []

def get_all_plakas() -> List[str]:
    """Tüm plakaları getir"""
    try:
        data = fetch_all_paginated('yakit', select='plaka')
        return sorted(list(set(row['plaka'] for row in data)))
    except:
        return []

def get_all_araclar() -> List[Dict]:
    """Tüm araçları getir"""
    try:
        return fetch_all_paginated('araclar', order='plaka.asc')
    except:
        return []

def add_arac(plaka: str, sahip: str, arac_tipi: str, notlar: str = '') -> Dict:
    """Yeni araç ekle"""
    try:
        data = {
            'plaka': plaka,
            'sahip': sahip,
            'arac_tipi': arac_tipi,
            'notlar': notlar,
            'aktif': 1
        }
        supabase_request('araclar', method='POST', data=data)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def update_arac(plaka: str, sahip: str, arac_tipi: str, aktif: int, notlar: str = '') -> Dict:
    """Araç güncelle"""
    try:
        data = {
            'sahip': sahip,
            'arac_tipi': arac_tipi,
            'aktif': aktif,
            'notlar': notlar
        }
        supabase_request(f'araclar?plaka=eq.{urllib.parse.quote(plaka)}', method='PATCH', data=data)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def delete_arac(plaka: str) -> Dict:
    """Araç sil"""
    try:
        supabase_request(f'araclar?plaka=eq.{urllib.parse.quote(plaka)}', method='DELETE')
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def bulk_import_araclar() -> Dict:
    """Veritabanındaki tüm plakaları araçlar tablosuna ekle"""
    try:
        all_plakas = get_all_plakas()
        existing = get_all_araclar()
        existing_plakas = set(arac['plaka'] for arac in existing)

        eklenen = 0
        for plaka in all_plakas:
            if plaka not in existing_plakas:
                add_arac(plaka, 'BİZİM', 'KARGO ARACI')
                eklenen += 1

        return {
            'status': 'success',
            'eklenen': eklenen,
            'toplam': len(existing_plakas) + eklenen
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_plakalar_by_type(arac_tipi: str = None) -> List[str]:
    """Araç tipine göre plakaları getir"""
    try:
        if arac_tipi == 'binek':
            filters = {'arac_tipi': 'eq.BİNEK ARAÇ', 'aktif': 'eq.1', 'sahip': 'eq.BİZİM'}
        elif arac_tipi == 'is_makinesi':
            filters = {'arac_tipi': 'eq.İŞ MAKİNESİ', 'aktif': 'eq.1', 'sahip': 'eq.BİZİM'}
        elif arac_tipi == 'kargo':
            filters = {'arac_tipi': 'eq.KARGO ARACI', 'aktif': 'eq.1', 'sahip': 'eq.BİZİM'}
        else:
            return get_all_plakas()

        data = fetch_all_paginated('araclar', select='plaka', filters=filters)
        return sorted([row['plaka'] for row in data])
    except:
        return []

def update_arac_bulk_sahip(plakalar: List[str], sahip: str) -> int:
    """Toplu araç sahip güncelle"""
    basarili = 0
    for plaka in plakalar:
        try:
            supabase_request(f'araclar?plaka=eq.{urllib.parse.quote(plaka)}', method='PATCH', data={'sahip': sahip})
            basarili += 1
        except:
            pass
    return basarili

def update_arac_bulk_aktif(plakalar: List[str], aktif: int) -> int:
    """Toplu araç aktif/pasif güncelle"""
    basarili = 0
    for plaka in plakalar:
        try:
            supabase_request(f'araclar?plaka=eq.{urllib.parse.quote(plaka)}', method='PATCH', data={'aktif': aktif})
            basarili += 1
        except:
            pass
    return basarili

def get_muhasebe_data(baslangic_tarihi: str = None, bitis_tarihi: str = None, plaka: str = None) -> Dict:
    """Muhasebe verilerini hesapla"""
    try:
        agirlik_filters = {}
        if baslangic_tarihi and bitis_tarihi:
            agirlik_filters['tarih'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            agirlik_filters['tarih'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            agirlik_filters['tarih'] = f'lte.{bitis_tarihi}'
        if plaka:
            agirlik_filters['plaka'] = f'eq.{urllib.parse.quote(plaka)}'

        agirlik_data = fetch_all_paginated('agirlik', filters=agirlik_filters)

        yakit_filters = {}
        if baslangic_tarihi and bitis_tarihi:
            yakit_filters['islem_tarihi'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            yakit_filters['islem_tarihi'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            yakit_filters['islem_tarihi'] = f'lte.{bitis_tarihi}'
        if plaka:
            yakit_filters['plaka'] = f'eq.{urllib.parse.quote(plaka)}'

        yakit_data = fetch_all_paginated('yakit', filters=yakit_filters)

        toplam_gelir = sum(float(row.get('miktar', 0) or 0) * 50 for row in agirlik_data)
        toplam_gider = sum(float(row.get('satir_tutari', 0) or 0) for row in yakit_data)
        net_kar = toplam_gelir - toplam_gider
        kar_marji = (net_kar / toplam_gelir * 100) if toplam_gelir > 0 else 0

        plaka_bazli = {}
        for row in agirlik_data:
            p = row['plaka']
            if p not in plaka_bazli:
                plaka_bazli[p] = {'gelir': 0, 'gider': 0}
            plaka_bazli[p]['gelir'] += float(row.get('miktar', 0) or 0) * 50

        for row in yakit_data:
            p = row['plaka']
            if p not in plaka_bazli:
                plaka_bazli[p] = {'gelir': 0, 'gider': 0}
            plaka_bazli[p]['gider'] += float(row.get('satir_tutari', 0) or 0)

        for p in plaka_bazli:
            plaka_bazli[p]['kar'] = plaka_bazli[p]['gelir'] - plaka_bazli[p]['gider']

        return {
            'status': 'success',
            'toplam_gelir': round(toplam_gelir, 2),
            'toplam_gider': round(toplam_gider, 2),
            'net_kar': round(net_kar, 2),
            'kar_marji': round(kar_marji, 2),
            'plaka_bazli': plaka_bazli
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_yakit_data() -> List[Dict]:
    """Aktif araçların yakıt verilerini çek"""
    try:
        return fetch_all_paginated('yakit', order='islem_tarihi.desc')
    except:
        return []

def get_agirlik_data() -> List[Dict]:
    """Aktif araçların ağırlık verilerini çek"""
    try:
        return fetch_all_paginated('agirlik', order='tarih.desc')
    except:
        return []

def get_arac_takip_data() -> List[Dict]:
    """Araç takip verilerini çek"""
    try:
        return fetch_all_paginated('arac_takip', order='created_at.desc')
    except:
        return []

def get_yakit_by_plaka(plaka: str) -> List[Dict]:
    """Belirli bir plakaya ait yakıt verilerini getir"""
    try:
        return fetch_all_paginated('yakit', filters={'plaka': f'eq.{urllib.parse.quote(plaka)}'}, order='islem_tarihi.desc')
    except:
        return []

def get_agirlik_by_plaka(plaka: str, sadece_urun: bool = False) -> List[Dict]:
    """Belirli bir plakaya ait ağırlık verilerini getir"""
    try:
        filters = {'plaka': f'eq.{urllib.parse.quote(plaka)}'}
        if sadece_urun:
            filters['birim'] = 'not.in.(Adet,adet,ADET)'
        return fetch_all_paginated('agirlik', filters=filters, order='tarih.desc')
    except:
        return []

def get_arac_takip_by_plaka(plaka: str) -> List[Dict]:
    """Belirli bir plakaya ait araç takip verilerini getir"""
    try:
        return fetch_all_paginated('arac_takip', filters={'plaka': f'eq.{urllib.parse.quote(plaka)}'}, order='created_at.desc')
    except:
        return []

def check_database_exists() -> bool:
    """Supabase bağlantısını kontrol et"""
    try:
        get_database_info()
        return True
    except:
        return False

# ============================================================
# REMOVED: SQLite Compatibility Layer
# Railway uses Supabase only - no local SQLite database
# ============================================================
