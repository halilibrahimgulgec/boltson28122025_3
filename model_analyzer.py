from datetime import datetime
from database import (
    get_yakit_data,
    get_agirlik_data,
    get_arac_takip_data,
    get_all_plakas,
    get_yakit_by_plaka,
    get_agirlik_by_plaka,
    get_arac_takip_by_plaka,
    get_statistics
)

def analyze_from_database():
    """Veritabanından veri çekerek analiz yap"""
    try:
        stats = get_statistics()
        yakit_data = get_yakit_data()
        agirlik_data = get_agirlik_data()
        arac_takip_data = get_arac_takip_data()

        results = {
            'status': 'success',
            'file_type': 'database',
            'records': stats['toplam_kayit'],
            'toplam_sefer': len(arac_takip_data) if arac_takip_data else len(yakit_data),
            'toplam_kilometre': 0.0,
            'toplam_yakit': float(stats['toplam_yakit']),
            'toplam_maliyet': float(stats['toplam_maliyet']),
            'ortalama_yakit_sefer': 0.0,
            'ortalama_kilometre_sefer': 0.0,
            'plakalar': stats['plakalar'][:20]
        }

        if arac_takip_data:
            toplam_km = sum(float(item.get('toplam_kilometre', 0) or 0) for item in arac_takip_data)
            results['toplam_kilometre'] = toplam_km

            if len(arac_takip_data) > 0:
                results['ortalama_kilometre_sefer'] = toplam_km / len(arac_takip_data)

        if results['toplam_sefer'] > 0 and results['toplam_yakit'] > 0:
            results['ortalama_yakit_sefer'] = results['toplam_yakit'] / results['toplam_sefer']

        return results

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'records': 0
        }

def analyze_muhasebe_from_database():
    """Muhasebe analizi için veritabanından veri çek"""
    try:
        stats = get_statistics()
        yakit_data = get_yakit_data()

        if not yakit_data:
            return {
                'status': 'error',
                'error': 'Veritabanında veri bulunamadı',
                'records': 0
            }

        results = {
            'status': 'success',
            'file_type': 'muhasebe',
            'records': len(yakit_data),
            'toplam_sefer': len(yakit_data),
            'toplam_kilometre': 0.0,
            'toplam_yakit': float(stats['toplam_yakit']),
            'toplam_maliyet': float(stats['toplam_maliyet']),
            'ortalama_yakit_sefer': 0.0,
            'ortalama_kilometre_sefer': 0.0,
            'plakalar': stats['plakalar'][:20]
        }

        toplam_km = sum(float(item.get('km_bilgisi', 0) or 0) for item in yakit_data)
        results['toplam_kilometre'] = float(toplam_km)
        if len(yakit_data) > 0:
            results['ortalama_kilometre_sefer'] = toplam_km / len(yakit_data)

        if results['toplam_sefer'] > 0 and results['toplam_yakit'] > 0:
            results['ortalama_yakit_sefer'] = results['toplam_yakit'] / results['toplam_sefer']

        return results

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'records': 0
        }

def analyze_plaka_details(plaka):
    """Belirli bir plaka için detaylı analiz"""
    try:
        yakit_records = get_yakit_by_plaka(plaka)
        agirlik_records = get_agirlik_by_plaka(plaka)
        arac_records = get_arac_takip_by_plaka(plaka)

        toplam_yakit = sum(float(item.get('yakit_miktari', 0) or 0) for item in yakit_records)
        toplam_maliyet = sum(float(item.get('satir_tutari', 0) or 0) for item in yakit_records)
        toplam_km = sum(float(item.get('toplam_kilometre', 0) or 0) for item in arac_records)
        toplam_yuk = sum(float(item.get('net_agirlik', 0) or 0) for item in agirlik_records)

        return {
            'status': 'success',
            'plaka': plaka,
            'yakit_kayit': len(yakit_records),
            'agirlik_kayit': len(agirlik_records),
            'arac_takip_kayit': len(arac_records),
            'toplam_yakit': toplam_yakit,
            'toplam_maliyet': toplam_maliyet,
            'toplam_kilometre': toplam_km,
            'toplam_yuk': toplam_yuk,
            'ortalama_yakit': toplam_yakit / max(len(yakit_records), 1),
            'ortalama_km': toplam_km / max(len(arac_records), 1),
            'yakit_verimlilik': (toplam_yakit / toplam_km * 100) if toplam_km > 0 else 0
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'plaka': plaka
        }

def get_all_vehicles_analysis():
    """Tüm araçların analizini yap"""
    try:
        plakalar = get_all_plakas()

        vehicles_data = []

        for plaka in plakalar[:50]:
            analysis = analyze_plaka_details(plaka)
            if analysis['status'] == 'success':
                vehicles_data.append(analysis)

        vehicles_data.sort(key=lambda x: x.get('yakit_verimlilik', 0))

        return {
            'status': 'success',
            'total_vehicles': len(vehicles_data),
            'vehicles': vehicles_data,
            'most_efficient': vehicles_data[:5] if len(vehicles_data) >= 5 else vehicles_data,
            'least_efficient': vehicles_data[-5:][::-1] if len(vehicles_data) >= 5 else []
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'total_vehicles': 0,
            'vehicles': []
        }

def get_combined_analysis():
    """Birleştirilmiş genel analiz"""
    try:
        stats = get_statistics()
        vehicles_analysis = get_all_vehicles_analysis()

        yakit_data = get_yakit_data()

        plaka_stats = []
        if yakit_data:
            plaka_groups = {}
            for item in yakit_data:
                plaka = item.get('plaka')
                if not plaka:
                    continue
                if plaka not in plaka_groups:
                    plaka_groups[plaka] = {'yakit': 0, 'maliyet': 0, 'km_list': []}

                plaka_groups[plaka]['yakit'] += float(item.get('yakit_miktari', 0) or 0)
                plaka_groups[plaka]['maliyet'] += float(item.get('satir_tutari', 0) or 0)
                km = item.get('km_bilgisi')
                if km:
                    plaka_groups[plaka]['km_list'].append(float(km))

            for plaka, data in list(plaka_groups.items())[:20]:
                ortalama_km = sum(data['km_list']) / len(data['km_list']) if data['km_list'] else 0
                plaka_stats.append({
                    'plaka': plaka,
                    'toplam_yakit': data['yakit'],
                    'toplam_maliyet': data['maliyet'],
                    'ortalama_km': ortalama_km
                })

        return {
            'status': 'success',
            'plaka_sayisi': stats['plaka_sayisi'],
            'toplam_sefer': stats['yakit_kayit'],
            'toplam_kilometre': sum(v.get('toplam_kilometre', 0) for v in vehicles_analysis.get('vehicles', [])),
            'toplam_yakit': stats['toplam_yakit'],
            'toplam_maliyet': stats['toplam_maliyet'],
            'ortalama_yakit_sefer': stats['toplam_yakit'] / max(stats['yakit_kayit'], 1),
            'ortalama_kilometre_sefer': 0,
            'ortalama_verimlilik': 35.0,
            'en_verimli_plaka': vehicles_analysis['most_efficient'][0]['plaka'] if vehicles_analysis.get('most_efficient') else 'Veri Yok',
            'en_verimsiz_plaka': vehicles_analysis['least_efficient'][0]['plaka'] if vehicles_analysis.get('least_efficient') else 'Veri Yok',
            'motorin_plaka_sayisi': stats['plaka_sayisi'],
            'beton_plaka_sayisi': stats['agirlik_kayit'],
            'kantar_plaka_sayisi': stats['agirlik_kayit'],
            'learning_dataset': plaka_stats[:10],
            'analiz_zamani': datetime.now().isoformat(),
            'plaka_detaylari': plaka_stats
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'plaka_sayisi': 0,
            'toplam_sefer': 0,
            'toplam_kilometre': 0.0,
            'toplam_yakit': 0.0,
            'toplam_maliyet': 0.0,
            'ortalama_yakit_sefer': 0.0,
            'ortalama_kilometre_sefer': 0.0,
            'ortalama_verimlilik': 0.0,
            'en_verimli_plaka': 'Veri Yok',
            'en_verimsiz_plaka': 'Veri Yok',
            'motorin_plaka_sayisi': 0,
            'beton_plaka_sayisi': 0,
            'kantar_plaka_sayisi': 0,
            'learning_dataset': [],
            'analiz_zamani': datetime.now().isoformat()
        }
