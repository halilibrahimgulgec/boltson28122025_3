import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_cors import CORS
from datetime import datetime
import logging
from dotenv import load_dotenv
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import hashlib
import json
import urllib.request

load_dotenv()

# Helper functions for data upload
def create_record_hash(record: dict) -> str:
    """Kayıt için benzersiz hash oluştur (duplicate kontrolü için)"""
    key_parts = []
    for key in sorted(record.keys()):
        if record[key] is not None:
            key_parts.append(f"{key}:{record[key]}")
    hash_string = '|'.join(key_parts)
    return hashlib.md5(hash_string.encode()).hexdigest()

def get_existing_hashes(table: str) -> set:
    """Tablodaki mevcut kayıtların hash'lerini al"""
    try:
        from database import SUPABASE_URL, SUPABASE_KEY
        url = f'{SUPABASE_URL}/rest/v1/{table}?select=record_hash'

        req = urllib.request.Request(url, method='GET')
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {row.get('record_hash') for row in data if row.get('record_hash')}
    except:
        return set()

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-here'

# Jinja2 template'lere Python built-in fonksiyonları ekle
app.jinja_env.globals.update(zip=zip)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup logging
logger.info("=" * 50)
logger.info("KARGO TAKİP SİSTEMİ - BAŞLATILIYOR")
logger.info(f"PORT: {os.environ.get('PORT', 'belirtilmemiş')}")
logger.info(f"SUPABASE_URL var mı: {bool(os.environ.get('VITE_SUPABASE_URL') or os.environ.get('SUPABASE_URL'))}")
logger.info(f"SUPABASE_KEY var mı: {bool(os.environ.get('VITE_SUPABASE_ANON_KEY') or os.environ.get('SUPABASE_ANAHTAR'))}")
logger.info("=" * 50)

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'port': os.environ.get('PORT', 'unknown')
    }), 200

@app.route('/')
def index():
    """Ana sayfa - Yakıt tahmin sistemi"""
    try:
        from database import get_database_info, get_statistics
        db_info = get_database_info()
        db_info['stats'] = get_statistics()
        return render_template('index.html', db_info=db_info)
    except Exception as e:
        logger.error(f"Index route error: {e}")
        # Boş veri ile devam et
        db_info = {
            'exists': False,
            'yakit_count': 0,
            'agirlik_count': 0,
            'arac_takip_count': 0,
            'total_records': 0,
            'stats': {
                'toplam_yakit': 0,
                'toplam_maliyet': 0,
                'plaka_sayisi': 0,
                'plakalar': [],
                'yakit_kayit': 0,
                'agirlik_kayit': 0,
                'arac_takip_kayit': 0,
                'toplam_kayit': 0
            }
        }
        return render_template('index.html', db_info=db_info)

@app.route('/muhasebe')
def muhasebe():
    """Muhasebe sayfası"""
    return render_template('muhasebe.html')

@app.route('/veri_yukleme')
def veri_yukleme():
    """Veri yükleme sayfası"""
    return render_template('veri_yukleme.html')

@app.route('/api/database-stats')
def api_database_stats():
    """Veritabanı istatistiklerini döndür"""
    try:
        from database import get_database_info, get_statistics
        db_info = get_database_info()
        stats = get_statistics()

        return jsonify({
            'yakit_count': db_info.get('yakit_count', 0),
            'agirlik_count': db_info.get('agirlik_count', 0),
            'arac_takip_count': db_info.get('arac_takip_count', 0),
            'plaka_sayisi': stats.get('plaka_sayisi', 0),
            'total_records': db_info.get('total_records', 0)
        })
    except Exception as e:
        logger.error(f"Database stats error: {e}")
        return jsonify({
            'yakit_count': 0,
            'agirlik_count': 0,
            'arac_takip_count': 0,
            'plaka_sayisi': 0,
            'total_records': 0
        })

@app.route('/api/upload-excel', methods=['POST'])
def api_upload_excel():
    """Excel dosyası yükle"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Dosya bulunamadı'}), 400

        file = request.files['file']
        file_type = request.form.get('type', '')

        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Sadece Excel dosyaları (.xlsx, .xls) desteklenir'}), 400

        # Excel dosyasını oku
        df = pd.read_excel(file)

        # Sütun isimlerini normalize et (Türkçe karakter + boşluk temizle)
        df.columns = df.columns.str.strip().str.lower()
        df.columns = df.columns.str.replace('ı', 'i').str.replace('ğ', 'g').str.replace('ü', 'u').str.replace('ş', 's').str.replace('ö', 'o').str.replace('ç', 'c')
        df.columns = df.columns.str.replace(' ', '_').str.replace('.', '')

        logger.info(f"Excel kolonları: {', '.join(df.columns.tolist()[:15])}")

        total = len(df)
        inserted = 0
        duplicates = 0
        skipped = 0

        # Dosya tipine göre işle
        if file_type == 'yakit':
            from database import supabase_insert_batch

            # Mevcut hash'leri al
            existing_hashes = get_existing_hashes('yakit')

            records = []
            for _, row in df.iterrows():
                # Sütun isimlerini esnek ara
                plaka = None
                for col in ['plaka', 'plate', 'arac', 'arac_plaka']:
                    if col in df.columns and pd.notna(row.get(col)):
                        plaka = str(row.get(col, '')).strip()
                        break

                yakit_miktari = None
                for col in ['yakit_miktari', 'miktar', 'litre', 'lt', 'yakit']:
                    if col in df.columns and pd.notna(row.get(col)):
                        val = float(row.get(col, 0))
                        if val > 0:
                            yakit_miktari = val
                            break

                # Boş kayıtları atla
                if not plaka or not yakit_miktari:
                    skipped += 1
                    continue

                birim_fiyat = 0.0
                for col in ['birim_fiyat', 'fiyat', 'birim', 'price']:
                    if col in df.columns and pd.notna(row.get(col)):
                        birim_fiyat = float(row.get(col, 0))
                        break

                satir_tutari = 0.0
                for col in ['satir_tutari', 'tutar', 'total', 'toplam']:
                    if col in df.columns and pd.notna(row.get(col)):
                        satir_tutari = float(row.get(col, 0))
                        break

                record = {
                    'plaka': plaka,
                    'islem_tarihi': str(row.get('islem_tarihi', '')) if pd.notna(row.get('islem_tarihi')) else None,
                    'saat': str(row.get('saat', '')) if pd.notna(row.get('saat')) else None,
                    'yakit_miktari': str(yakit_miktari),
                    'birim_fiyat': str(birim_fiyat),
                    'satir_tutari': str(satir_tutari),
                    'stok_adi': str(row.get('stok_adi', 'MOTORİN')) if pd.notna(row.get('stok_adi')) else 'MOTORİN',
                    'km_bilgisi': str(float(row.get('km_bilgisi', 0))) if pd.notna(row.get('km_bilgisi')) and float(row.get('km_bilgisi', 0)) > 0 else None
                }

                record_hash = create_record_hash(record)
                if record_hash in existing_hashes:
                    duplicates += 1
                    continue

                record['record_hash'] = record_hash
                records.append(record)

            # Batch insert
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                if supabase_insert_batch('yakit', batch):
                    inserted += len(batch)
                else:
                    logger.error(f"Batch insert failed for yakit records {i}-{i+len(batch)}")

        elif file_type == 'agirlik':
            from database import supabase_insert_batch

            existing_hashes = get_existing_hashes('agirlik')

            records = []
            for _, row in df.iterrows():
                # Esnek sütun arama
                plaka = None
                for col in ['plaka', 'plate', 'arac']:
                    if col in df.columns and pd.notna(row.get(col)):
                        plaka = str(row.get(col, '')).strip()
                        break

                net_agirlik = None
                for col in ['net_agirlik', 'agirlik', 'net', 'tonaj', 'ton']:
                    if col in df.columns and pd.notna(row.get(col)):
                        val = float(row.get(col, 0))
                        if val > 0:
                            net_agirlik = val
                            break

                # Boş kayıtları atla
                if not plaka or not net_agirlik:
                    skipped += 1
                    continue

                record = {
                    'tarih': str(row.get('tarih', '')) if pd.notna(row.get('tarih')) else None,
                    'miktar': str(float(row.get('miktar', 0))) if pd.notna(row.get('miktar')) else None,
                    'birim': str(row.get('birim', '')) if pd.notna(row.get('birim')) else None,
                    'net_agirlik': str(net_agirlik),
                    'plaka': plaka,
                    'adres': str(row.get('adres', '')) if pd.notna(row.get('adres')) else None,
                    'islem_noktasi': str(row.get('islem_noktasi', '')) if pd.notna(row.get('islem_noktasi')) else None,
                    'cari_adi': str(row.get('cari_adi', '')) if pd.notna(row.get('cari_adi')) else None
                }

                record_hash = create_record_hash(record)
                if record_hash in existing_hashes:
                    duplicates += 1
                    continue

                record['record_hash'] = record_hash
                records.append(record)

            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                if supabase_insert_batch('agirlik', batch):
                    inserted += len(batch)
                else:
                    logger.error(f"Batch insert failed for agirlik records {i}-{i+len(batch)}")

        elif file_type == 'arac-takip':
            from database import supabase_insert_batch

            existing_hashes = get_existing_hashes('arac_takip')

            records = []
            for _, row in df.iterrows():
                # Esnek sütun arama
                plaka = None
                for col in ['plaka', 'plate', 'arac']:
                    if col in df.columns and pd.notna(row.get(col)):
                        plaka = str(row.get(col, '')).strip()
                        break

                toplam_km = None
                for col in ['toplam_kilometre', 'kilometre', 'km', 'mesafe']:
                    if col in df.columns and pd.notna(row.get(col)):
                        val = float(row.get(col, 0))
                        if val > 0:
                            toplam_km = val
                            break

                # Boş kayıtları atla
                if not plaka or not toplam_km:
                    skipped += 1
                    continue

                record = {
                    'plaka': plaka,
                    'sofor_adi': str(row.get('sofor_adi', '')) if pd.notna(row.get('sofor_adi')) else None,
                    'arac_gruplari': str(row.get('arac_gruplari', '')) if pd.notna(row.get('arac_gruplari')) else None,
                    'tarih': str(row.get('tarih', '')) if pd.notna(row.get('tarih')) else None,
                    'hareket_baslangic_tarihi': str(row.get('hareket_baslangic_tarihi', '')) if pd.notna(row.get('hareket_baslangic_tarihi')) else None,
                    'hareket_bitis_tarihi': str(row.get('hareket_bitis_tarihi', '')) if pd.notna(row.get('hareket_bitis_tarihi')) else None,
                    'baslangic_adresi': str(row.get('baslangic_adresi', '')) if pd.notna(row.get('baslangic_adresi')) else None,
                    'bitis_adresi': str(row.get('bitis_adresi', '')) if pd.notna(row.get('bitis_adresi')) else None,
                    'toplam_kilometre': str(toplam_km),
                    'hareket_suresi': str(row.get('hareket_suresi', '')) if pd.notna(row.get('hareket_suresi')) else None,
                    'rolanti_suresi': str(row.get('rolanti_suresi', '')) if pd.notna(row.get('rolanti_suresi')) else None,
                    'park_suresi': str(row.get('park_suresi', '')) if pd.notna(row.get('park_suresi')) else None,
                    'gunluk_yakit_tuketimi_l': str(float(row.get('gunluk_yakit_tuketimi_l', 0))) if pd.notna(row.get('gunluk_yakit_tuketimi_l')) else None
                }

                record_hash = create_record_hash(record)
                if record_hash in existing_hashes:
                    duplicates += 1
                    continue

                record['record_hash'] = record_hash
                records.append(record)

            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                if supabase_insert_batch('arac_takip', batch):
                    inserted += len(batch)
                else:
                    logger.error(f"Batch insert failed for arac_takip records {i}-{i+len(batch)}")

        else:
            return jsonify({'error': 'Geçersiz dosya tipi'}), 400

        logger.info(f"Upload summary - Total: {total}, Inserted: {inserted}, Duplicates: {duplicates}, Skipped: {skipped}")

        return jsonify({
            'success': True,
            'inserted': inserted,
            'duplicates': duplicates,
            'skipped': skipped,
            'total': total
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/plakalar')
def api_plakalar():
    """Plaka listesi API - araç tipine göre filtrelenebilir"""
    try:
        from database import get_plakalar_by_type, get_all_plakas

        arac_tipi = request.args.get('tip')

        if arac_tipi == 'binek':
            plakalar = get_plakalar_by_type('binek')
        elif arac_tipi == 'is_makinesi':
            plakalar = get_plakalar_by_type('is_makinesi')
        elif arac_tipi == 'kargo':
            plakalar = get_plakalar_by_type('kargo')
        else:
            plakalar = get_all_plakas()

        return jsonify({'plakalar': plakalar})
    except Exception as e:
        return jsonify({'plakalar': [], 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze():
    """Veritabanından analiz yap"""
    try:
        from database import get_database_info, hesapla_gercek_km, fetch_all_paginated, get_aktif_kargo_araclari

        # Model analyzer opsiyonel - yoksa devam et
        try:
            from model_analyzer import analyze_from_database
        except ImportError:
            analyze_from_database = None

        db_info = get_database_info()
        if not db_info.get('exists'):
            flash('❌ Veritabanı dosyası bulunamadı! Önce python excel_to_sqlite.py komutunu çalıştırın.', 'error')
            return redirect(url_for('index'))

        # Filtreleri al
        baslangic_tarihi = request.form.get('baslangic_tarihi') or None
        bitis_tarihi = request.form.get('bitis_tarihi') or None
        plaka = request.form.get('plaka') or None
        dahil_taseron = request.form.get('dahil_taseron') == '1'

        # Filtreleri kaydet
        session['filter_baslangic'] = baslangic_tarihi
        session['filter_bitis'] = bitis_tarihi
        session['filter_plaka'] = plaka
        session['dahil_taseron'] = dahil_taseron

        # Model analyzer kullan veya basit analiz yap
        if analyze_from_database:
            analysis_result = analyze_from_database()
        else:
            # Basit analiz - sadece istatistikler
            from database import get_statistics
            stats = get_statistics()
            analysis_result = {
                'status': 'success',
                'records': stats['toplam_kayit'],
                'toplam_sefer': stats['yakit_kayit'],
                'toplam_yakit': stats['toplam_yakit'],
                'toplam_maliyet': stats['toplam_maliyet'],
                'ortalama_yakit_sefer': stats['toplam_yakit'] / stats['yakit_kayit'] if stats['yakit_kayit'] > 0 else 0,
                'plakalar': stats['plakalar']
            }

        if analysis_result['status'] == 'error':
            flash(f'❌ Veritabanı analiz hatası: {analysis_result["error"]}', 'error')
            return redirect(url_for('index'))

        if analysis_result['records'] == 0:
            flash('❌ Veritabanında hiç kayıt yok! Excel dosyalarınızı python excel_to_sqlite.py ile yükleyin.', 'error')
            return redirect(url_for('index'))

        plakalar = []
        tahminler = []

        if analysis_result['toplam_yakit'] > 0 and len(analysis_result.get('plakalar', [])) > 0:
            # Aktif kargo araçlarını al
            aktif_kargo = get_aktif_kargo_araclari()

            # Tüm yakıt verilerini çek
            yakit_data = fetch_all_paginated('yakit', select='plaka,yakit_miktari')

            # Plakaya göre grupla
            yakit_by_plaka = {}
            for row in yakit_data:
                plaka_key = row.get('plaka')
                yakit_miktari = float(row.get('yakit_miktari', 0) or 0)

                if plaka_key and yakit_miktari > 0 and plaka_key in aktif_kargo:
                    if plaka_key not in yakit_by_plaka:
                        yakit_by_plaka[plaka_key] = []
                    yakit_by_plaka[plaka_key].append(yakit_miktari)

            arac_detaylari = []

            for plaka_key, yakit_list in yakit_by_plaka.items():
                toplam_yakit = sum(yakit_list)
                ortalama_yakit = toplam_yakit / len(yakit_list) if yakit_list else 0

                # KM hesaplama
                toplam_km = hesapla_gercek_km(plaka_key, baslangic_tarihi, bitis_tarihi)

                # Ağırlık verilerini çek
                agirlik_data = fetch_all_paginated('agirlik',
                                                   select='birim,miktar',
                                                   filters={'plaka': f'eq.{plaka_key}'})

                # Birim bazında verileri ayır
                kg_data = {'toplam': 0, 'sefer': 0}
                m2_data = {'toplam': 0, 'sefer': 0}
                m3_data = {'toplam': 0, 'sefer': 0}
                adet_data = {'toplam': 0, 'sefer': 0}
                mt_data = {'toplam': 0, 'sefer': 0}
                toplam_sefer = 0

                for ag_row in agirlik_data:
                    birim = (ag_row.get('birim') or '').upper()
                    miktar = float(ag_row.get('miktar', 0) or 0)

                    if miktar > 0:
                        if birim == 'KG':
                            kg_data['toplam'] += miktar
                            kg_data['sefer'] += 1
                            toplam_sefer += 1
                        elif birim == 'M2':
                            m2_data['toplam'] += miktar
                            m2_data['sefer'] += 1
                            toplam_sefer += 1
                        elif birim == 'M3':
                            m3_data['toplam'] += miktar
                            m3_data['sefer'] += 1
                            toplam_sefer += 1
                        elif birim == 'ADET':
                            adet_data['toplam'] += miktar
                            adet_data['sefer'] += 1
                        elif birim == 'MT':
                            mt_data['toplam'] += miktar
                            mt_data['sefer'] += 1
                            toplam_sefer += 1

                # Hesaplamalar
                km_litre_orani = round(toplam_km / toplam_yakit, 2) if toplam_yakit > 0 and toplam_km > 0 else None
                kg_litre_orani = round(kg_data['toplam'] / toplam_yakit, 2) if toplam_yakit > 0 and kg_data['toplam'] > 0 else None

                plakalar.append(plaka_key)
                tahminler.append(round(ortalama_yakit, 2))

                arac_detaylari.append({
                    'plaka': plaka_key,
                    'toplam_yakit': round(toplam_yakit, 2),
                    'toplam_km': round(toplam_km, 2) if toplam_km > 0 else None,
                    'sefer_sayisi': toplam_sefer,
                    'kg_toplam': round(kg_data['toplam'], 2) if kg_data['toplam'] > 0 else None,
                    'kg_sefer': kg_data['sefer'],
                    'm2_toplam': round(m2_data['toplam'], 2) if m2_data['toplam'] > 0 else None,
                    'm2_sefer': m2_data['sefer'],
                    'm3_toplam': round(m3_data['toplam'], 2) if m3_data['toplam'] > 0 else None,
                    'm3_sefer': m3_data['sefer'],
                    'adet_toplam': int(adet_data['toplam']) if adet_data['toplam'] > 0 else None,
                    'adet_sefer': adet_data['sefer'],
                    'mt_toplam': round(mt_data['toplam'], 2) if mt_data['toplam'] > 0 else None,
                    'mt_sefer': mt_data['sefer'],
                    'ortalama_yakit': round(ortalama_yakit, 2),
                    'km_litre_orani': km_litre_orani,
                    'kg_litre_orani': kg_litre_orani
                })
        else:
            flash(f'❌ Veritabanında yakıt verisi bulunamadı! Kayıt sayısı: {analysis_result["records"]}, Toplam yakıt: {analysis_result["toplam_yakit"]}, Plaka sayısı: {len(analysis_result.get("plakalar", []))}', 'error')
            return redirect(url_for('index'))

        flash('✅ Veritabanı analizi tamamlandı!', 'success')

        insights = {
            'toplam_yakit': analysis_result['toplam_yakit'],
            'toplam_maliyet': analysis_result['toplam_maliyet'],
            'ortalama_fiyat': analysis_result['toplam_maliyet'] / analysis_result['toplam_yakit'] if analysis_result['toplam_yakit'] > 0 else 0,
            'toplam_km': analysis_result.get('toplam_kilometre', 0)
        }

        genel_ozet = {
            'toplam_arac': len(arac_detaylari),
            'toplam_yakit': analysis_result['toplam_yakit'],
            'arac_tipi': 'Kargo Araçları'
        }

        from datetime import datetime
        return render_template('result.html',
                             tahminler=tahminler,
                             plakalar=plakalar,
                             sefer=analysis_result['toplam_sefer'],
                             yakit=round(analysis_result['toplam_yakit'], 2),
                             rolanti=round(analysis_result['ortalama_yakit_sefer'] * 0.6, 2),
                             egim="5.2",
                             ortalama_tahmin=round(sum(tahminler)/len(tahminler), 2) if tahminler else 0,
                             insights=insights,
                             arac_detaylari=arac_detaylari,
                             genel_ozet=genel_ozet,
                             analiz_tipi='kargo',
                             now=datetime.now())

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Upload hatası: {error_detail}")
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/muhasebe-analyze', methods=['POST'])
def muhasebe_analyze():
    """Muhasebe analizi"""
    try:
        from database import get_muhasebe_data

        baslangic_tarihi = request.form.get('baslangic_tarihi') or None
        bitis_tarihi = request.form.get('bitis_tarihi') or None
        plaka = request.form.get('plaka', '').strip()

        result = get_muhasebe_data(baslangic_tarihi, bitis_tarihi, plaka or None)

        if result['status'] == 'error':
            flash(f'❌ Hata: {result["message"]}', 'error')
            return redirect(url_for('muhasebe'))

        return render_template('muhasebe_result.html',
                             baslangic_tarihi=baslangic_tarihi or 'Başlangıç',
                             bitis_tarihi=bitis_tarihi or 'Bugün',
                             plaka=plaka or 'Tümü',
                             toplam_gelir=result['toplam_gelir'],
                             toplam_gider=result['toplam_gider'],
                             net_kar=result['net_kar'],
                             kar_marji=result['kar_marji'],
                             plaka_bazli=result['plaka_bazli'])

    except Exception as e:
        flash(f'Hata: {str(e)}', 'error')
        return redirect(url_for('muhasebe'))

@app.route('/database-status')
def database_status():
    """Veritabanı durumunu görsel olarak göster"""
    from database import get_database_info, get_statistics
    db_info = get_database_info()

    stats = {}
    if db_info.get('exists'):
        try:
            stats = get_statistics()
        except Exception as e:
            stats = {'error': str(e)}

    return render_template('database_status.html', db_info=db_info, stats=stats)

@app.route('/debug-info')
def debug_info():
    """Debug bilgisi JSON formatında"""
    from database import get_database_info, get_statistics
    db_info = get_database_info()

    stats = {}
    if db_info.get('exists'):
        try:
            stats = get_statistics()
        except Exception as e:
            stats = {'error': str(e)}

    return jsonify({
        'database': db_info,
        'statistics': stats
    })

@app.route('/ai-analysis')
def ai_analysis():
    """AI analiz sayfası"""
    from database import get_aktif_kargo_araclari
    plakalar = get_aktif_kargo_araclari()
    return render_template('ai_analysis.html', plakalar=plakalar)

@app.route('/ai-train', methods=['POST'])
def ai_train():
    """AI modellerini eğit"""
    try:
        from ai_model import YakitTahminModeli, AnomalTespitModeli

        # Yakıt tahmin modelini eğit
        tahmin_model = YakitTahminModeli()
        tahmin_result = tahmin_model.egit()

        # Anomali tespit modelini eğit
        anomali_model = AnomalTespitModeli()
        anomali_result = anomali_model.egit()

        if tahmin_result['status'] == 'success' and anomali_result['status'] == 'success':
            flash('✅ AI modelleri başarıyla eğitildi!', 'success')
            return jsonify({
                'status': 'success',
                'tahmin_model': tahmin_result,
                'anomali_model': anomali_result
            })
        else:
            error_msg = tahmin_result.get('message', '') or anomali_result.get('message', '')
            flash(f'❌ Model eğitimi hatası: {error_msg}', 'error')
            return jsonify({
                'status': 'error',
                'message': error_msg
            })
    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/ai-predict', methods=['POST'])
def ai_predict():
    """Yakıt tüketim tahmini yap"""
    try:
        from ai_model import YakitTahminModeli

        plaka = request.form.get('plaka')
        tarih = request.form.get('tarih')
        tahmin_tipi = request.form.get('tahmin_tipi', 'tek')

        model = YakitTahminModeli()

        if tahmin_tipi == 'gelecek_ay':
            result = model.gelecek_ay_tahmini(plaka)
        else:
            result = model.tahmin_yap(plaka, tarih)

        if result['status'] == 'success':
            return render_template('ai_predict_result.html', result=result, tahmin_tipi=tahmin_tipi)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('ai_analysis'))

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('ai_analysis'))

@app.route('/ai-anomaly', methods=['POST', 'GET'])
def ai_anomaly():
    """Anomali tespiti yap"""
    try:
        from ai_model import AnomalTespitModeli

        model = AnomalTespitModeli()
        result = model.anomali_tespit()

        if result['status'] == 'success':
            return render_template('ai_anomaly_result.html', result=result)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('ai_analysis'))

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('ai_analysis'))

@app.route('/anomaly-dashboard')
def anomaly_dashboard():
    """Anomali dashboard sayfası - filtreleme ve grafiklerle"""
    try:
        from ai_model import AnomalTespitModeli
        from database import get_all_plakas

        model = AnomalTespitModeli()
        result = model.anomali_tespit_detayli()

        if result['status'] == 'success':
            plakalar = get_all_plakas()
            return render_template('anomaly_dashboard.html',
                                 result=result,
                                 plakalar=plakalar)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('ai_analysis'))
    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('ai_analysis'))

@app.route('/ai-bulk-predict', methods=['POST'])
def ai_bulk_predict():
    """Tüm plakalar için toplu tahmin"""
    try:
        from ai_model import tum_plakalar_tahmini

        result = tum_plakalar_tahmini()

        if result['status'] == 'success':
            return render_template('ai_bulk_result.html', result=result)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('ai_analysis'))

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('ai_analysis'))

@app.route('/performans-analizi')
def performans_analizi():
    """Performans analizi sayfası"""
    from database import get_all_plakas
    plakalar = get_all_plakas()
    return render_template('performans_analizi.html', plakalar=plakalar)

@app.route('/performans-karsilastirma', methods=['POST'])
def performans_karsilastirma():
    """Tüm araçların performans karşılaştırması"""
    try:
        from ai_model import PerformansAnalizi

        ana_malzeme = request.form.get('ana_malzeme', '').strip()

        analiz = PerformansAnalizi()
        result = analiz.plaka_performans_karsilastirma(ana_malzeme_filtre=ana_malzeme if ana_malzeme else None)

        if result['status'] == 'success':
            return render_template('performans_karsilastirma.html', result=result, selected_malzeme=ana_malzeme)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('performans_analizi'))

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('performans_analizi'))

@app.route('/performans-detay', methods=['POST'])
def performans_detay():
    """Belirli bir araç için detaylı performans analizi"""
    try:
        from ai_model import PerformansAnalizi

        plaka = request.form.get('plaka')
        baslangic_tarihi = request.form.get('baslangic_tarihi') or None
        bitis_tarihi = request.form.get('bitis_tarihi') or None

        analiz = PerformansAnalizi()
        result = analiz.plaka_detay_analiz(plaka, baslangic_tarihi, bitis_tarihi)

        if result['status'] == 'success':
            return render_template('performans_detay.html', result=result)
        else:
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('performans_analizi'))

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('performans_analizi'))

@app.route('/performans-export-pdf', methods=['POST'])
def performans_export_pdf():
    """Performans karşılaştırma PDF export"""
    try:
        from ai_model import PerformansAnalizi
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io

        ana_malzeme = request.form.get('ana_malzeme', '').strip()

        analiz = PerformansAnalizi()
        result = analiz.plaka_performans_karsilastirma(ana_malzeme_filtre=ana_malzeme if ana_malzeme else None)

        if result['status'] != 'success':
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('performans_analizi'))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1*cm, rightMargin=1*cm)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20,
            alignment=1
        )

        malzeme_text = f" - {ana_malzeme}" if ana_malzeme else ""
        title = Paragraph(f"Araç Performans Karşılaştırması{malzeme_text}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.5*cm))

        ozet_data = [
            ['Metrik', 'Değer'],
            ['Ortalama KM/Litre', f"{result['ortalama_km_litre']:.2f} km/L"],
            ['Ortalama Ton/Yakıt', f"{result['ortalama_ton_yakit']:.2f} ton/L"],
            ['Toplam Araç Sayısı', str(result['toplam_arac'])]
        ]

        ozet_table = Table(ozet_data, colWidths=[8*cm, 8*cm])
        ozet_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(ozet_table)
        elements.append(Spacer(1, 1*cm))

        table_data = [['Plaka', 'Ana Malzeme', 'Toplam Yakıt (L)', 'Toplam KM', 'Toplam Tonaj', 'KM/Litre', 'KM/Maliyet', 'Ton/Yakıt', 'Verimlilik']]

        for arac in result['veriler']:
            table_data.append([
                arac['plaka'],
                arac['ana_malzeme'] if arac['ana_malzeme'] else 'Bilinmiyor',
                f"{arac['toplam_yakit']:.1f}",
                f"{arac['toplam_km']:.0f}",
                f"{arac['toplam_tonaj']:.2f}",
                f"{arac['km_litre']:.2f}" if arac['km_litre'] else 'N/A',
                f"{arac['km_maliyet']:.2f} TL" if arac['km_maliyet'] else 'N/A',
                f"{arac['ton_yakit']:.2f}" if arac['ton_yakit'] else 'N/A',
                arac['verimlilik']
            ])

        data_table = Table(table_data, colWidths=[3*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        elements.append(data_table)

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'performans_raporu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

    except Exception as e:
        flash(f'❌ PDF oluşturulamadı: {str(e)}', 'error')
        return redirect(url_for('performans_analizi'))

@app.route('/performans-export-excel', methods=['POST'])
def performans_export_excel():
    """Performans karşılaştırma Excel export"""
    try:
        from ai_model import PerformansAnalizi
        import pandas as pd
        import io

        ana_malzeme = request.form.get('ana_malzeme', '').strip()

        analiz = PerformansAnalizi()
        result = analiz.plaka_performans_karsilastirma(ana_malzeme_filtre=ana_malzeme if ana_malzeme else None)

        if result['status'] != 'success':
            flash(f'❌ {result["message"]}', 'error')
            return redirect(url_for('performans_analizi'))

        df_data = []
        for arac in result['veriler']:
            df_data.append({
                'Plaka': arac['plaka'],
                'Ana Malzeme': arac['ana_malzeme'] if arac['ana_malzeme'] else 'Bilinmiyor',
                'Toplam Yakıt (L)': arac['toplam_yakit'],
                'Toplam KM': arac['toplam_km'],
                'Toplam Tonaj': arac['toplam_tonaj'],
                'KM/Litre': arac['km_litre'] if arac['km_litre'] else 'N/A',
                'KM/Maliyet (TL)': arac['km_maliyet'] if arac['km_maliyet'] else 'N/A',
                'Ton/Yakıt': arac['ton_yakit'] if arac['ton_yakit'] else 'N/A',
                'Verimlilik': arac['verimlilik']
            })

        df = pd.DataFrame(df_data)

        ozet_df = pd.DataFrame({
            'Metrik': ['Ortalama KM/Litre', 'Ortalama Ton/Yakıt', 'Toplam Araç Sayısı'],
            'Değer': [
                f"{result['ortalama_km_litre']:.2f} km/L",
                f"{result['ortalama_ton_yakit']:.2f} ton/L",
                str(result['toplam_arac'])
            ]
        })

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            ozet_df.to_excel(writer, sheet_name='Özet', index=False)
            df.to_excel(writer, sheet_name='Detaylı Veri', index=False)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'performans_raporu_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        flash(f'❌ Excel oluşturulamadı: {str(e)}', 'error')
        return redirect(url_for('performans_analizi'))

@app.route('/arac-yonetimi')
def arac_yonetimi():
    """Araç yönetimi sayfası"""
    from database import get_all_araclar

    araclar = get_all_araclar()

    kargo_sayisi = len([a for a in araclar if a['arac_tipi'] == 'KARGO ARACI' and a['aktif'] == 1])
    is_makinesi_sayisi = len([a for a in araclar if a['arac_tipi'] == 'İŞ MAKİNESİ'])
    binek_sayisi = len([a for a in araclar if a['arac_tipi'] == 'BİNEK ARAÇ'])

    return render_template('arac_yonetimi.html',
                         araclar=araclar,
                         kargo_sayisi=kargo_sayisi,
                         is_makinesi_sayisi=is_makinesi_sayisi,
                         binek_sayisi=binek_sayisi)

@app.route('/arac-ekle', methods=['POST'])
def arac_ekle():
    """Yeni araç ekle"""
    try:
        from database import add_arac

        plaka = request.form.get('plaka', '').strip().upper()
        sahip = request.form.get('sahip')
        arac_tipi = request.form.get('arac_tipi')
        notlar = request.form.get('notlar', '').strip()

        result = add_arac(plaka, sahip, arac_tipi, notlar)

        if result['status'] == 'success':
            flash(f'✅ {plaka} plakası başarıyla eklendi!', 'success')
        else:
            flash(f'❌ {result["message"]}', 'error')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-guncelle', methods=['POST'])
def arac_guncelle():
    """Araç güncelle"""
    try:
        from database import update_arac

        plaka = request.form.get('plaka')
        sahip = request.form.get('sahip')
        arac_tipi = request.form.get('arac_tipi')
        aktif = int(request.form.get('aktif', 1))
        notlar = request.form.get('notlar', '').strip()

        result = update_arac(plaka, sahip, arac_tipi, aktif, notlar)

        if result['status'] == 'success':
            flash(f'✅ {plaka} başarıyla güncellendi!', 'success')
        else:
            flash(f'❌ {result["message"]}', 'error')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-sil', methods=['POST'])
def arac_sil():
    """Araç sil"""
    try:
        from database import delete_arac

        plaka = request.form.get('plaka')
        result = delete_arac(plaka)

        if result['status'] == 'success':
            flash(f'✅ {plaka} silindi!', 'success')
        else:
            flash(f'❌ {result["message"]}', 'error')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-toplu-sil', methods=['POST'])
def arac_toplu_sil():
    """Toplu araç sil"""
    try:
        from database import delete_arac

        plakalar = request.form.getlist('plakalar')

        if not plakalar:
            flash('❌ Silinecek araç seçilmedi!', 'error')
            return redirect(url_for('arac_yonetimi'))

        basarili = 0
        basarisiz = 0

        for plaka in plakalar:
            result = delete_arac(plaka)
            if result['status'] == 'success':
                basarili += 1
            else:
                basarisiz += 1

        if basarili > 0:
            flash(f'✅ {basarili} araç başarıyla silindi!', 'success')
        if basarisiz > 0:
            flash(f'⚠️ {basarisiz} araç silinemedi!', 'error')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-toplu-sahip', methods=['POST'])
def arac_toplu_sahip():
    """Toplu araç sahip güncelle (BİZİM/TAŞERON)"""
    try:
        from database import update_arac_bulk_sahip

        plakalar = request.form.getlist('plakalar')
        sahip = request.form.get('sahip')

        if not plakalar:
            flash('❌ Araç seçilmedi!', 'error')
            return redirect(url_for('arac_yonetimi'))

        basarili = update_arac_bulk_sahip(plakalar, sahip)
        flash(f'✅ {basarili} araç "{sahip}" olarak güncellendi!', 'success')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-toplu-durum', methods=['POST'])
def arac_toplu_durum():
    """Toplu araç durum güncelle (Aktif/Pasif)"""
    try:
        from database import update_arac_bulk_aktif

        plakalar = request.form.getlist('plakalar')
        aktif = request.form.get('aktif')

        if not plakalar:
            flash('❌ Araç seçilmedi!', 'error')
            return redirect(url_for('arac_yonetimi'))

        basarili = update_arac_bulk_aktif(plakalar, int(aktif))
        durum_text = 'AKTİF' if aktif == '1' else 'PASİF'
        flash(f'✅ {basarili} araç "{durum_text}" yapıldı!', 'success')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-toplu-import', methods=['POST'])
def arac_toplu_import():
    """Veritabanındaki tüm plakaları araçlar tablosuna ekle - HIZLI VERSİYON"""
    try:
        from database import bulk_import_araclar

        result = bulk_import_araclar()

        if result['status'] == 'success':
            flash(f'✅ {result["eklenen"]} yeni plaka eklendi. Toplam: {result["toplam"]} araç.', 'success')
        else:
            flash(f'❌ Hata: {result["message"]}', 'error')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/export-excel', methods=['POST'])
def export_excel():
    """Analiz sonuçlarını Excel'e dönüştür"""
    try:
        data = request.get_json()
        arac_detaylari = data.get('arac_detaylari', [])

        if not arac_detaylari:
            return jsonify({'status': 'error', 'message': 'Veri bulunamadı'}), 400

        # Türkçe kolon isimleri ile dönüştür
        logger.info(f"Excel export: {len(arac_detaylari)} araç verisi alındı")
        excel_data = []
        for arac in arac_detaylari:
            row = {
                'Plaka': arac.get('plaka', ''),
                'Toplam Yakıt (L)': arac.get('toplam_yakit', 0),
            }

            # Kargo araçları için ekstra kolonlar
            if 'sefer_sayisi' in arac:
                row['Toplam KM'] = arac.get('toplam_km', 0) or 0
                row['Toplam Sefer'] = arac.get('sefer_sayisi', 0)
                row['KG Toplam'] = arac.get('kg_toplam', 0) or 0
                row['KG Sefer'] = arac.get('kg_sefer', 0)
                row['M2 Toplam'] = arac.get('m2_toplam', 0) or 0
                row['M2 Sefer'] = arac.get('m2_sefer', 0)
                row['M3 Toplam'] = arac.get('m3_toplam', 0) or 0
                row['M3 Sefer'] = arac.get('m3_sefer', 0)
                row['Adet Toplam'] = arac.get('adet_toplam', 0) or 0
                row['Adet Sefer'] = arac.get('adet_sefer', 0)
                row['MT Toplam'] = arac.get('mt_toplam', 0) or 0
                row['MT Sefer'] = arac.get('mt_sefer', 0)
                row['Ortalama Yakıt (L)'] = arac.get('ortalama_yakit', 0)
                row['KM/Litre'] = arac.get('km_litre_orani', 0) or 0
                row['KG/Litre'] = arac.get('kg_litre_orani', 0) or 0
            # Binek ve iş makineleri için kolonlar
            else:
                row['Toplam KM'] = arac.get('toplam_km', 0) or 0
                row['Yakıt Alımları'] = arac.get('yakit_alimlari', 0)
                row['Ortalama Yakıt (L)'] = arac.get('ortalama_yakit', 0)
                row['Tüketim (L/100km)'] = arac.get('tuketim_100km', 0) or 0

            excel_data.append(row)

        logger.info(f"Excel export: {len(excel_data)} satır hazırlandı")
        df = pd.DataFrame(excel_data)
        logger.info(f"Excel export: DataFrame oluşturuldu, shape: {df.shape}")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Analiz Sonuçları', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Analiz Sonuçları']

            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })

            number_format = workbook.add_format({'num_format': '#,##0.00'})

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 18)

                # Sayısal kolonlar için format
                if col_num > 0:  # İlk kolon plaka
                    for row_num in range(1, len(df) + 1):
                        worksheet.write(row_num, col_num, df.iloc[row_num-1, col_num], number_format)

        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'yakit_analizi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        logger.error(f"Excel export error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    """Analiz sonuçlarını PDF'e dönüştür"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.pagesizes import A4
        import os

        data = request.get_json()
        arac_detaylari = data.get('arac_detaylari', [])
        analiz_tipi = data.get('analiz_tipi', '')

        if not arac_detaylari:
            return jsonify({'status': 'error', 'message': 'Veri bulunamadı'}), 400

        # Türkçe karakter desteği için Liberation Serif (Times New Roman benzeri) fontlarını kaydet
        try:
            font_paths = [
                '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
                '/usr/share/fonts/liberation-serif/LiberationSerif-Regular.ttf',
                '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
                '/System/Library/Fonts/Times New Roman.ttf',
                'C:\\Windows\\Fonts\\times.ttf',
            ]
            font_bold_paths = [
                '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
                '/usr/share/fonts/liberation-serif/LiberationSerif-Bold.ttf',
                '/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf',
                '/System/Library/Fonts/Times New Roman Bold.ttf',
                'C:\\Windows\\Fonts\\timesbd.ttf',
            ]

            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('TimesRoman', font_path))
                    font_loaded = True
                    logger.info(f"Font loaded: {font_path}")
                    break

            for font_path in font_bold_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('TimesRoman-Bold', font_path))
                    logger.info(f"Bold font loaded: {font_path}")
                    break

            if font_loaded:
                default_font = 'TimesRoman'
                bold_font = 'TimesRoman-Bold'
            else:
                # Fallback: ReportLab'in yerleşik Times-Roman fontu (sınırlı Türkçe)
                default_font = 'Times-Roman'
                bold_font = 'Times-Bold'
                logger.warning("Liberation Serif bulunamadı, Times-Roman kullanılıyor")
        except Exception as e:
            logger.error(f"Font loading error: {e}")
            default_font = 'Times-Roman'
            bold_font = 'Times-Bold'

        buffer = io.BytesIO()
        # DİKEY (portrait) A4 format
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=30)
        elements = []

        styles = getSampleStyleSheet()

        # Türkçe karakter desteği için stil
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=bold_font,
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=20
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName=bold_font,
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=15
        )

        elements.append(Paragraph('Yakıt Analiz Raporu', title_style))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f'Tarih: {datetime.now().strftime("%d.%m.%Y %H:%M")}', styles['Normal']))
        elements.append(Spacer(1, 0.8*cm))

        # Araç tipine göre tablo oluştur
        logger.info(f"PDF export: {len(arac_detaylari)} araç verisi alındı")
        is_kargo = any('sefer_sayisi' in arac for arac in arac_detaylari)

        if is_kargo:
            # Kargo araçları için TÜM ARAÇLARI içeren detaylı tablo
            elements.append(Paragraph(f'Kargo Araçları Analizi ({len(arac_detaylari)} Araç)', subtitle_style))

            # A4 dikey için optimize edilmiş tablo
            table_data = [['#', 'Plaka', 'Yakıt (L)', 'KM', 'Sefer', 'KG', 'KM/L', 'KG/L']]

            for idx, arac in enumerate(arac_detaylari, 1):
                toplam_yakit = arac.get('toplam_yakit') or 0
                toplam_km = arac.get('toplam_km') or 0
                sefer_sayisi = arac.get('sefer_sayisi') or 0
                kg_toplam = arac.get('kg_toplam') or 0
                km_litre = arac.get('km_litre_orani') or 0
                kg_litre = arac.get('kg_litre_orani') or 0

                table_data.append([
                    str(idx),
                    arac.get('plaka', ''),
                    f"{toplam_yakit:.1f}",
                    f"{toplam_km:.0f}" if toplam_km > 0 else '-',
                    str(sefer_sayisi),
                    f"{kg_toplam:.0f}" if kg_toplam > 0 else '-',
                    f"{km_litre:.2f}" if km_litre > 0 else '-',
                    f"{kg_litre:.0f}" if kg_litre > 0 else '-'
                ])

            # A4 dikey: 21cm genişlik, kenar boşlukları çıkarınca ~18cm kullanılabilir
            kargo_table = Table(table_data, colWidths=[1*cm, 3*cm, 2.2*cm, 2*cm, 1.8*cm, 2.2*cm, 2*cm, 2*cm])
            kargo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), bold_font),
                ('FONTNAME', (0, 1), (-1, -1), default_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            elements.append(kargo_table)
        else:
            # Araç tipini belirle
            arac_tipi = 'İş Makinesi' if analiz_tipi == 'is_makinesi' else 'Binek Araç'

            # Binek ve iş makineleri için TÜM ARAÇLARI içeren tablo
            elements.append(Paragraph(f'{arac_tipi} Analizi ({len(arac_detaylari)} Araç)', subtitle_style))

            table_data = [['#', 'Plaka', 'Toplam Yakıt (L)', 'Toplam KM', 'Yakıt Alımları', 'Tüketim (L/100km)']]

            for idx, arac in enumerate(arac_detaylari, 1):
                toplam_yakit = arac.get('toplam_yakit') or 0
                toplam_km = arac.get('toplam_km') or 0
                yakit_alimlari = arac.get('yakit_alimlari') or 0
                tuketim = arac.get('tuketim_100km') or 0

                table_data.append([
                    str(idx),
                    arac.get('plaka', ''),
                    f"{toplam_yakit:.2f}",
                    f"{toplam_km:.0f}" if toplam_km > 0 else '-',
                    str(yakit_alimlari),
                    f"{tuketim:.2f}" if tuketim > 0 else '-'
                ])

            # A4 dikey için optimize edilmiş
            main_table = Table(table_data, colWidths=[1*cm, 3.5*cm, 3.5*cm, 3*cm, 3*cm, 3.5*cm])
            main_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), bold_font),
                ('FONTNAME', (0, 1), (-1, -1), default_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            elements.append(main_table)

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'yakit_analizi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

    except Exception as e:
        logger.error(f"PDF export error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/kargo-arac-filtre')
def kargo_arac_filtre():
    """Kargo araç filtre sayfası"""
    try:
        from database import get_aktif_kargo_araclari
        kargo_plakalar = get_aktif_kargo_araclari()
        logger.info(f"📊 Kargo araç sayısı: {len(kargo_plakalar)}")
        return render_template('kargo_arac_filtre.html', plakalar=kargo_plakalar)
    except Exception as e:
        logger.error(f"❌ Kargo filtre hatası: {e}")
        return render_template('kargo_arac_filtre.html', plakalar=[])

@app.route('/binek-arac-filtre')
def binek_arac_filtre():
    """Binek araç filtre sayfası"""
    try:
        from database import get_aktif_binek_araclar
        binek_plakalar = get_aktif_binek_araclar(dahil_taseron=False)
        logger.info(f"📊 Binek araç sayısı: {len(binek_plakalar)}")
        return render_template('binek_arac_filtre.html', plakalar=binek_plakalar)
    except Exception as e:
        logger.error(f"❌ Binek filtre hatası: {e}")
        return render_template('binek_arac_filtre.html', plakalar=[])

@app.route('/is-makinesi-filtre')
def is_makinesi_filtre():
    """İş makinesi filtre sayfası"""
    try:
        from database import get_aktif_is_makineleri
        is_makinesi_plakalar = get_aktif_is_makineleri(dahil_taseron=False)
        logger.info(f"📊 İş makinesi sayısı: {len(is_makinesi_plakalar)}")
        return render_template('is_makinesi_filtre.html', plakalar=is_makinesi_plakalar)
    except Exception as e:
        logger.error(f"❌ İş makinesi filtre hatası: {e}")
        return render_template('is_makinesi_filtre.html', plakalar=[])

@app.route('/ai-assistant')
def ai_assistant():
    """AI Asistan sayfası"""
    return render_template('ai_assistant.html')

@app.route('/api/assistant/status')
def assistant_status():
    """Ollama servis durumunu kontrol et"""
    try:
        from ollama_assistant import OllamaAssistant
        assistant = OllamaAssistant(model='llama3.1')
        status = assistant.check_ollama_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/assistant/ask', methods=['POST'])
def assistant_ask():
    """Asistana soru sor"""
    try:
        from ollama_assistant import OllamaAssistant

        data = request.get_json()
        question = data.get('question', '')

        if not question:
            return jsonify({'status': 'error', 'message': 'Soru boş olamaz'})

        # Türkçe destekli model kullan
        assistant = OllamaAssistant(model='llama3.2')
        result = assistant.ask_with_db_query(question)

        # Excel veya PDF export varsa session'a kaydet
        if result.get('export_type') in ['excel', 'pdf']:
            import base64
            session['export_file'] = base64.b64encode(result['file_data']).decode('utf-8')
            session['export_type'] = result['export_type']
            session['export_filename'] = result['filename']
            result['download_url'] = '/api/assistant/download'

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/assistant/download')
def assistant_download():
    """Export dosyasını indir"""
    try:
        import base64

        if 'export_file' not in session:
            return jsonify({'status': 'error', 'message': 'İndirilecek dosya bulunamadı'})

        file_data = base64.b64decode(session['export_file'])
        export_type = session.get('export_type', 'excel')
        filename = session.get('export_filename', 'rapor.xlsx')

        # Session'ı temizle
        session.pop('export_file', None)
        session.pop('export_type', None)
        session.pop('export_filename', None)

        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if export_type == 'excel' else 'application/pdf'

        return send_file(
            io.BytesIO(file_data),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/assistant/history')
def assistant_history():
    """Sohbet geçmişini getir"""
    try:
        from ollama_assistant import OllamaAssistant
        assistant = OllamaAssistant(model='llama3.2')
        history = assistant.get_chat_history()
        return jsonify({'status': 'success', 'history': history})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/assistant/clear', methods=['POST'])
def assistant_clear():
    """Sohbet geçmişini temizle"""
    try:
        from ollama_assistant import OllamaAssistant
        assistant = OllamaAssistant(model='llama3.2')
        result = assistant.clear_history()
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/binek-arac-analizi', methods=['GET', 'POST'])
def binek_arac_analizi():
    """Binek araç analizi sayfası"""
    try:
        from database import get_aktif_binek_araclar, hesapla_gercek_km, fetch_all_paginated
        import urllib.parse

        # Filtreleri al
        baslangic_tarihi = request.form.get('baslangic_tarihi') if request.method == 'POST' else None
        bitis_tarihi = request.form.get('bitis_tarihi') if request.method == 'POST' else None
        plaka_filtre = request.form.get('plaka') if request.method == 'POST' else None
        dahil_taseron = request.form.get('dahil_taseron') == '1' if request.method == 'POST' else False

        aktif_binek = get_aktif_binek_araclar(dahil_taseron=dahil_taseron)
        print(f"🔍 DEBUG - Aktif binek araçlar ({len(aktif_binek)}): {aktif_binek}")

        if not aktif_binek:
            flash('⚠️ Aktif binek araç bulunamadı. Araç Yönetimi\'nden binek araç ekleyin.', 'warning')
            return render_template('result.html',
                                 arac_detaylari=[],
                                 genel_ozet={'arac_tipi': 'Binek Araç', 'toplam_arac': 0, 'toplam_yakit': 0})

        # Yakıt verilerini çek
        filters = {}
        if baslangic_tarihi and bitis_tarihi:
            filters['islem_tarihi'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            filters['islem_tarihi'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            filters['islem_tarihi'] = f'lte.{bitis_tarihi}'

        print(f"🔍 DEBUG - Tarih filtreleri: Başlangıç={baslangic_tarihi}, Bitiş={bitis_tarihi}")
        print(f"🔍 DEBUG - Supabase filters: {filters}")

        yakit_data = fetch_all_paginated('yakit', select='plaka,yakit_miktari', filters=filters)
        print(f"🔍 DEBUG - Yakıt verisi sayısı: {len(yakit_data)}")

        # Plakaya göre grupla
        yakit_by_plaka = {}
        for row in yakit_data:
            plaka_key = row.get('plaka')
            yakit_miktari = float(row.get('yakit_miktari', 0) or 0)

            # Filtreleme
            if plaka_key and yakit_miktari > 0 and plaka_key in aktif_binek:
                if plaka_filtre and plaka_key != plaka_filtre:
                    continue

                if plaka_key not in yakit_by_plaka:
                    yakit_by_plaka[plaka_key] = []
                yakit_by_plaka[plaka_key].append(yakit_miktari)

        print(f"🔍 DEBUG - Bulunan binek araç sayısı: {len(yakit_by_plaka)}")
        print(f"🔍 DEBUG - Yakıt verileri: {list(yakit_by_plaka.keys())}")

        if not yakit_by_plaka:
            # Veri bulunamadı, tarih aralığını göster
            mesaj = '⚠️ Seçilen tarih aralığında binek araç yakıt verisi bulunamadı.'
            if not baslangic_tarihi and not bitis_tarihi:
                mesaj = '⚠️ Binek araçlar için yakıt verisi bulunamadı. Son veri: 29 Ekim 2025'
            flash(mesaj, 'warning')
            return render_template('result.html',
                                 arac_detaylari=[],
                                 genel_ozet={'arac_tipi': 'Binek Araç', 'toplam_arac': 0, 'toplam_yakit': 0},
                                 analiz_tipi='binek',
                                 sefer=0,
                                 yakit=0,
                                 ortalama_tahmin=0,
                                 plakalar=[],
                                 tahminler=[],
                                 now=datetime.now(),
                                 tarih_bilgi=f"Başlangıç: {baslangic_tarihi or 'Tümü'}, Bitiş: {bitis_tarihi or 'Tümü'}")

        arac_detaylari = []
        toplam_yakit_genel = 0

        for plaka_key, yakit_list in yakit_by_plaka.items():
            toplam_yakit = sum(yakit_list)
            ortalama_yakit = toplam_yakit / len(yakit_list) if yakit_list else 0
            yakit_alimlari = len(yakit_list)

            # KM hesaplama
            toplam_km = hesapla_gercek_km(plaka_key, baslangic_tarihi, bitis_tarihi)

            tuketim = (toplam_yakit / toplam_km * 100) if toplam_km > 0 else 0

            arac_detaylari.append({
                'plaka': plaka_key,
                'toplam_yakit': toplam_yakit,
                'toplam_km': toplam_km,
                'ortalama_yakit': ortalama_yakit,
                'yakit_alimlari': yakit_alimlari,
                'tuketim_100km': tuketim
            })

            toplam_yakit_genel += toplam_yakit

        genel_ozet = {
            'toplam_arac': len(arac_detaylari),
            'toplam_yakit': toplam_yakit_genel,
            'arac_tipi': 'Binek Araç'
        }

        plakalar = [arac['plaka'] for arac in arac_detaylari]
        tahminler = [round(arac['ortalama_yakit'], 2) for arac in arac_detaylari]

        toplam_yakit_alimlari = sum(arac['yakit_alimlari'] for arac in arac_detaylari)

        return render_template('result.html',
                             arac_detaylari=arac_detaylari,
                             genel_ozet=genel_ozet,
                             analiz_tipi='binek',
                             sefer=toplam_yakit_alimlari,
                             yakit=round(toplam_yakit_genel, 2),
                             ortalama_tahmin=round(toplam_yakit_genel / toplam_yakit_alimlari, 2) if toplam_yakit_alimlari > 0 else 0,
                             plakalar=plakalar,
                             tahminler=tahminler,
                             now=datetime.now())

    except Exception as e:
        flash(f'❌ Binek araç analiz hatası: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))

@app.route('/kargo-arac-analizi', methods=['GET', 'POST'])
def kargo_arac_analizi():
    """Kargo araç analizi sayfası"""
    try:
        from database import get_aktif_kargo_araclari, hesapla_gercek_km, fetch_all_paginated
        import urllib.parse

        # Filtreleri al
        baslangic_tarihi = request.form.get('baslangic_tarihi') if request.method == 'POST' else None
        bitis_tarihi = request.form.get('bitis_tarihi') if request.method == 'POST' else None
        plaka_filtre = request.form.get('plaka') if request.method == 'POST' else None
        dahil_taseron = request.form.get('dahil_taseron') == '1' if request.method == 'POST' else False

        aktif_kargo = get_aktif_kargo_araclari()
        print(f"🔍 DEBUG - Aktif kargo araçlar ({len(aktif_kargo)}): {aktif_kargo}")

        if not aktif_kargo:
            flash('⚠️ Aktif kargo araç bulunamadı. Araç Yönetimi\'nden kargo araç ekleyin.', 'warning')
            return render_template('result.html',
                                 arac_detaylari=[],
                                 genel_ozet={'arac_tipi': 'Kargo Aracı', 'toplam_arac': 0, 'toplam_yakit': 0})

        # Yakıt verilerini çek
        yakit_filters = {}
        if baslangic_tarihi and bitis_tarihi:
            yakit_filters['islem_tarihi'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            yakit_filters['islem_tarihi'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            yakit_filters['islem_tarihi'] = f'lte.{bitis_tarihi}'

        print(f"🔍 DEBUG - Tarih filtreleri: Başlangıç={baslangic_tarihi}, Bitiş={bitis_tarihi}")
        print(f"🔍 DEBUG - Yakıt filter: {yakit_filters}")

        yakit_data = fetch_all_paginated('yakit', select='plaka,yakit_miktari', filters=yakit_filters)
        print(f"🔍 DEBUG - Yakıt verisi sayısı: {len(yakit_data)}")

        # Ağırlık verilerini çek (agirlik tablosundan)
        agirlik_filters = {}
        if baslangic_tarihi and bitis_tarihi:
            agirlik_filters['tarih'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            agirlik_filters['tarih'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            agirlik_filters['tarih'] = f'lte.{bitis_tarihi}'

        kargo_data = fetch_all_paginated('agirlik', select='plaka,net_agirlik,birim,miktar', filters=agirlik_filters)
        print(f"🔍 DEBUG - Ağırlık verisi sayısı: {len(kargo_data)}")

        # Plakaya göre grupla
        yakit_by_plaka = {}
        for row in yakit_data:
            plaka_key = row.get('plaka')
            yakit_miktari = float(row.get('yakit_miktari', 0) or 0)

            if plaka_key and yakit_miktari > 0 and plaka_key in aktif_kargo:
                if plaka_filtre and plaka_key != plaka_filtre:
                    continue

                if plaka_key not in yakit_by_plaka:
                    yakit_by_plaka[plaka_key] = []
                yakit_by_plaka[plaka_key].append(yakit_miktari)

        # Kargo verilerini plakaya göre grupla
        kargo_by_plaka = {}
        for row in kargo_data:
            plaka_key = row.get('plaka')
            if plaka_key and plaka_key in aktif_kargo:
                if plaka_filtre and plaka_key != plaka_filtre:
                    continue

                if plaka_key not in kargo_by_plaka:
                    kargo_by_plaka[plaka_key] = {
                        'kg_toplam': 0, 'kg_sefer': 0,
                        'm2_toplam': 0, 'm2_sefer': 0,
                        'm3_toplam': 0, 'm3_sefer': 0,
                        'adet_toplam': 0, 'adet_sefer': 0,
                        'mt_toplam': 0, 'mt_sefer': 0
                    }

                net_agirlik = float(row.get('net_agirlik', 0) or 0)
                birim = (row.get('birim') or '').upper()
                miktar = float(row.get('miktar', 0) or 0)

                # Net ağırlık varsa KG olarak kaydet (ton ise kg'ye çevir)
                if net_agirlik > 0:
                    kg_deger = net_agirlik
                    if 'TON' in birim.upper():
                        kg_deger = net_agirlik * 1000
                    kargo_by_plaka[plaka_key]['kg_toplam'] += kg_deger
                    kargo_by_plaka[plaka_key]['kg_sefer'] += 1

                # Birim bazında diğer ölçüler
                if miktar > 0:
                    if 'M2' in birim or 'M²' in birim:
                        kargo_by_plaka[plaka_key]['m2_toplam'] += miktar
                        kargo_by_plaka[plaka_key]['m2_sefer'] += 1
                    elif 'M3' in birim or 'M³' in birim:
                        kargo_by_plaka[plaka_key]['m3_toplam'] += miktar
                        kargo_by_plaka[plaka_key]['m3_sefer'] += 1
                    elif 'ADET' in birim or 'AD' in birim:
                        kargo_by_plaka[plaka_key]['adet_toplam'] += int(miktar)
                        kargo_by_plaka[plaka_key]['adet_sefer'] += 1
                    elif 'MT' in birim or 'METRE' in birim:
                        kargo_by_plaka[plaka_key]['mt_toplam'] += miktar
                        kargo_by_plaka[plaka_key]['mt_sefer'] += 1

        print(f"🔍 DEBUG - Bulunan kargo araç sayısı: {len(yakit_by_plaka)}")

        arac_detaylari = []
        toplam_yakit_genel = 0
        toplam_sefer = 0

        for plaka_key, yakit_list in yakit_by_plaka.items():
            toplam_yakit = sum(yakit_list)
            ortalama_yakit = toplam_yakit / len(yakit_list) if yakit_list else 0
            sefer_sayisi = len(yakit_list)

            # KM hesaplama
            toplam_km = hesapla_gercek_km(plaka_key, baslangic_tarihi, bitis_tarihi)

            # Kargo verileri
            kargo_info = kargo_by_plaka.get(plaka_key, {})
            kg_toplam = kargo_info.get('kg_toplam', 0)

            # Verimlilik metrikleri
            km_litre_orani = round(toplam_km / toplam_yakit, 2) if toplam_yakit > 0 else 0
            kg_litre_orani = round(kg_toplam / toplam_yakit, 2) if toplam_yakit > 0 else 0

            arac_detaylari.append({
                'plaka': plaka_key,
                'toplam_yakit': toplam_yakit,
                'toplam_km': toplam_km,
                'ortalama_yakit': round(ortalama_yakit, 2),
                'sefer_sayisi': sefer_sayisi,
                'kg_toplam': kargo_info.get('kg_toplam', 0),
                'kg_sefer': kargo_info.get('kg_sefer', 0),
                'm2_toplam': kargo_info.get('m2_toplam', 0),
                'm2_sefer': kargo_info.get('m2_sefer', 0),
                'm3_toplam': kargo_info.get('m3_toplam', 0),
                'm3_sefer': kargo_info.get('m3_sefer', 0),
                'adet_toplam': kargo_info.get('adet_toplam', 0),
                'adet_sefer': kargo_info.get('adet_sefer', 0),
                'mt_toplam': kargo_info.get('mt_toplam', 0),
                'mt_sefer': kargo_info.get('mt_sefer', 0),
                'km_litre_orani': km_litre_orani,
                'kg_litre_orani': kg_litre_orani
            })

            toplam_yakit_genel += toplam_yakit
            toplam_sefer += sefer_sayisi

        genel_ozet = {
            'toplam_arac': len(arac_detaylari),
            'toplam_yakit': toplam_yakit_genel,
            'arac_tipi': 'Kargo Aracı'
        }

        plakalar = [arac['plaka'] for arac in arac_detaylari]
        tahminler = [arac['ortalama_yakit'] for arac in arac_detaylari]

        return render_template('result.html',
                             arac_detaylari=arac_detaylari,
                             genel_ozet=genel_ozet,
                             analiz_tipi='kargo',
                             sefer=toplam_sefer,
                             yakit=round(toplam_yakit_genel, 2),
                             ortalama_tahmin=round(toplam_yakit_genel / toplam_sefer, 2) if toplam_sefer > 0 else 0,
                             plakalar=plakalar,
                             tahminler=tahminler,
                             now=datetime.now())

    except Exception as e:
        flash(f'❌ Kargo araç analiz hatası: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))

@app.route('/is-makinesi-analizi', methods=['GET', 'POST'])
def is_makinesi_analizi():
    """İş makinesi analizi sayfası"""
    try:
        from database import get_aktif_is_makineleri, hesapla_gercek_km, fetch_all_paginated
        import urllib.parse

        # Filtreleri al
        baslangic_tarihi = request.form.get('baslangic_tarihi') if request.method == 'POST' else None
        bitis_tarihi = request.form.get('bitis_tarihi') if request.method == 'POST' else None
        plaka_filtre = request.form.get('plaka') if request.method == 'POST' else None
        dahil_taseron = request.form.get('dahil_taseron') == '1' if request.method == 'POST' else False

        aktif_makineler = get_aktif_is_makineleri(dahil_taseron=dahil_taseron)

        if not aktif_makineler:
            flash('⚠️ Aktif iş makinesi bulunamadı. Araç Yönetimi\'nden iş makinesi ekleyin.', 'warning')
            return render_template('result.html',
                                 arac_detaylari=[],
                                 genel_ozet={'arac_tipi': 'İş Makinesi', 'toplam_arac': 0, 'toplam_yakit': 0})

        # Yakıt verilerini çek
        filters = {}
        if baslangic_tarihi and bitis_tarihi:
            filters['islem_tarihi'] = f'and(gte.{baslangic_tarihi},lte.{bitis_tarihi})'
        elif baslangic_tarihi:
            filters['islem_tarihi'] = f'gte.{baslangic_tarihi}'
        elif bitis_tarihi:
            filters['islem_tarihi'] = f'lte.{bitis_tarihi}'

        yakit_data = fetch_all_paginated('yakit', select='plaka,yakit_miktari', filters=filters)

        # Plakaya göre grupla
        yakit_by_plaka = {}
        for row in yakit_data:
            plaka_key = row.get('plaka')
            yakit_miktari = float(row.get('yakit_miktari', 0) or 0)

            # Filtreleme
            if plaka_key and yakit_miktari > 0 and plaka_key in aktif_makineler:
                if plaka_filtre and plaka_key != plaka_filtre:
                    continue

                if plaka_key not in yakit_by_plaka:
                    yakit_by_plaka[plaka_key] = []
                yakit_by_plaka[plaka_key].append(yakit_miktari)

        arac_detaylari = []
        toplam_yakit_genel = 0

        for plaka_key, yakit_list in yakit_by_plaka.items():
            toplam_yakit = sum(yakit_list)
            ortalama_yakit = toplam_yakit / len(yakit_list) if yakit_list else 0
            yakit_alimlari = len(yakit_list)

            # KM hesaplama
            toplam_km = hesapla_gercek_km(plaka_key, baslangic_tarihi, bitis_tarihi)

            tuketim = (toplam_yakit / toplam_km * 100) if toplam_km > 0 else 0

            arac_detaylari.append({
                'plaka': plaka_key,
                'toplam_yakit': toplam_yakit,
                'toplam_km': toplam_km,
                'ortalama_yakit': ortalama_yakit,
                'yakit_alimlari': yakit_alimlari,
                'tuketim_100km': tuketim
            })

            toplam_yakit_genel += toplam_yakit

        genel_ozet = {
            'toplam_arac': len(arac_detaylari),
            'toplam_yakit': toplam_yakit_genel,
            'arac_tipi': 'İş Makinesi'
        }

        plakalar = [arac['plaka'] for arac in arac_detaylari]
        tahminler = [round(arac['ortalama_yakit'], 2) for arac in arac_detaylari]

        toplam_yakit_alimlari = sum(arac['yakit_alimlari'] for arac in arac_detaylari)

        return render_template('result.html',
                             arac_detaylari=arac_detaylari,
                             genel_ozet=genel_ozet,
                             analiz_tipi='is_makinesi',
                             sefer=toplam_yakit_alimlari,
                             yakit=round(toplam_yakit_genel, 2),
                             ortalama_tahmin=round(toplam_yakit_genel / toplam_yakit_alimlari, 2) if toplam_yakit_alimlari > 0 else 0,
                             plakalar=plakalar,
                             tahminler=tahminler,
                             now=datetime.now())

    except Exception as e:
        flash(f'❌ İş makinesi analiz hatası: {str(e)}', 'error')
        import traceback
        traceback.print_exc()
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*50)
    print("🚀 Flask Yakıt Tahmin Sistemi Başlatılıyor...")
    print("="*50)
    print(f"📍 URL: http://localhost:{port}")
    print("📁 Veritabanı: kargo_data.db")
    print(f"🔍 Durum: http://localhost:{port}/database-status")
    print("="*50 + "\n")

    app.run(debug=False, host='0.0.0.0', port=port)
