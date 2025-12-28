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

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-here'

# Jinja2 template'lere Python built-in fonksiyonları ekle
app.jinja_env.globals.update(zip=zip)

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Ana sayfa - Yakıt tahmin sistemi"""
    from database import get_database_info, get_statistics
    db_info = get_database_info()
    db_info['stats'] = get_statistics()
    return render_template('index.html', db_info=db_info)

@app.route('/muhasebe')
def muhasebe():
    """Muhasebe sayfası"""
    return render_template('muhasebe.html')

@app.route('/api/plakalar')
def api_plakalar():
    """Plaka listesi API - araç tipine göre filtrelenebilir"""
    try:
        import sqlite3
        conn = sqlite3.connect('kargo_data.db')
        cursor = conn.cursor()

        arac_tipi = request.args.get('tip')

        if arac_tipi == 'binek':
            cursor.execute('''
                SELECT DISTINCT y.plaka
                FROM yakit y
                JOIN araclar a ON y.plaka = a.plaka
                WHERE a.arac_tipi = 'BİNEK ARAÇ'
                AND a.aktif = 1
                AND a.sahip = 'BİZİM'
                ORDER BY y.plaka
            ''')
        elif arac_tipi == 'is_makinesi':
            cursor.execute('''
                SELECT DISTINCT y.plaka
                FROM yakit y
                JOIN araclar a ON y.plaka = a.plaka
                WHERE a.arac_tipi = 'İŞ MAKİNESİ'
                AND a.aktif = 1
                AND a.sahip = 'BİZİM'
                ORDER BY y.plaka
            ''')
        elif arac_tipi == 'kargo':
            cursor.execute('''
                SELECT DISTINCT y.plaka
                FROM yakit y
                JOIN araclar a ON y.plaka = a.plaka
                WHERE a.arac_tipi = 'KARGO ARACI'
                AND a.aktif = 1
                AND a.sahip = 'BİZİM'
                ORDER BY y.plaka
            ''')
        else:
            cursor.execute('SELECT DISTINCT plaka FROM yakit ORDER BY plaka')

        plakalar = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify({'plakalar': plakalar})
    except Exception as e:
        return jsonify({'plakalar': [], 'error': str(e)})

@app.route('/analyze', methods=['POST'])
def analyze():
    """Veritabanından analiz yap"""
    try:
        from model_analyzer import analyze_from_database
        from database import get_database_info

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

        analysis_result = analyze_from_database()

        if analysis_result['status'] == 'error':
            flash(f'❌ Veritabanı analiz hatası: {analysis_result["error"]}', 'error')
            return redirect(url_for('index'))

        if analysis_result['records'] == 0:
            flash('❌ Veritabanında hiç kayıt yok! Excel dosyalarınızı python excel_to_sqlite.py ile yükleyin.', 'error')
            return redirect(url_for('index'))

        plakalar = []
        tahminler = []

        if analysis_result['toplam_yakit'] > 0 and len(analysis_result.get('plakalar', [])) > 0:
            from database import get_db_connection, hesapla_gercek_km
            conn = get_db_connection()
            cursor = conn.cursor()

            # Detaylı analiz: yakıt ve km bilgileri - SADECE AKTİF KARGO ARAÇLARI
            cursor.execute('''
                SELECT
                    y.plaka,
                    SUM(y.yakit_miktari) as toplam_yakit,
                    AVG(y.yakit_miktari) as ortalama_yakit
                FROM yakit y
                INNER JOIN araclar a ON y.plaka = a.plaka
                WHERE y.yakit_miktari IS NOT NULL
                AND y.yakit_miktari > 0
                AND a.aktif = 1
                AND a.arac_tipi = 'KARGO ARACI'
                GROUP BY y.plaka
                ORDER BY ortalama_yakit DESC
            ''')

            yakit_rows = cursor.fetchall()
            arac_detaylari = []

            for row in yakit_rows:
                plaka = row['plaka']
                toplam_yakit = float(row['toplam_yakit'])
                ortalama_yakit = float(row['ortalama_yakit'])

                # DOĞRU KM HESAPLAMA: Ardışık kayıtlar arasındaki farkları topla (TARİH FİLTRELİ)
                toplam_km = hesapla_gercek_km(plaka, conn, baslangic_tarihi, bitis_tarihi)

                # Ağırlık ve SEFER bilgisini BİRİM BAZINDA agirlik tablosundan al
                # SADECE miktar > 0 ve NOT NULL olanlar sefer sayılır
                cursor.execute('''
                    SELECT
                        birim,
                        SUM(miktar) as toplam,
                        COUNT(*) as sefer_sayisi
                    FROM agirlik
                    WHERE plaka = ?
                    AND miktar IS NOT NULL
                    AND miktar > 0
                    GROUP BY birim
                ''', (plaka,))

                agirlik_rows = cursor.fetchall()

                # Birim bazında verileri ayır
                kg_data = {'toplam': 0, 'sefer': 0}
                m2_data = {'toplam': 0, 'sefer': 0}
                m3_data = {'toplam': 0, 'sefer': 0}
                adet_data = {'toplam': 0, 'sefer': 0}
                mt_data = {'toplam': 0, 'sefer': 0}
                toplam_sefer = 0

                for ag_row in agirlik_rows:
                    birim = ag_row['birim'] if ag_row['birim'] else ''
                    toplam = float(ag_row['toplam']) if ag_row['toplam'] else 0
                    sefer = int(ag_row['sefer_sayisi']) if ag_row['sefer_sayisi'] else 0

                    if birim.upper() == 'KG':
                        kg_data = {'toplam': toplam, 'sefer': sefer}
                        toplam_sefer += sefer
                    elif birim.upper() == 'M2':
                        m2_data = {'toplam': toplam, 'sefer': sefer}
                        toplam_sefer += sefer
                    elif birim.upper() == 'M3':
                        m3_data = {'toplam': toplam, 'sefer': sefer}
                        toplam_sefer += sefer
                    elif birim.upper() == 'ADET':
                        adet_data = {'toplam': toplam, 'sefer': sefer}
                    elif birim.upper() == 'MT':
                        mt_data = {'toplam': toplam, 'sefer': sefer}
                        toplam_sefer += sefer

                # Hesaplamalar - KM veya yük bilgisi yoksa None döndür
                # km_litre_orani: 1 litre ile kaç km gidiyor (örn: 5.2 km/litre)
                km_litre_orani = round(toplam_km / toplam_yakit, 2) if toplam_yakit > 0 else None
                # kg_litre_orani: 1 litre ile kaç kg taşıdı (örn: 1200 kg/litre) - YÜKSEK = VERİMLİ
                kg_litre_orani = round(kg_data['toplam'] / toplam_yakit, 2) if toplam_yakit > 0 and kg_data['toplam'] > 0 else None

                plakalar.append(plaka)
                tahminler.append(round(ortalama_yakit, 2))

                arac_detaylari.append({
                    'plaka': plaka,
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

            conn.close()
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
        from database import get_db_connection

        plakalar = request.form.getlist('plakalar')
        sahip = request.form.get('sahip')

        if not plakalar:
            flash('❌ Araç seçilmedi!', 'error')
            return redirect(url_for('arac_yonetimi'))

        conn = get_db_connection()
        cursor = conn.cursor()

        basarili = 0
        for plaka in plakalar:
            cursor.execute('UPDATE araclar SET sahip = ? WHERE plaka = ?', (sahip, plaka))
            basarili += 1

        conn.commit()
        conn.close()

        flash(f'✅ {basarili} araç "{sahip}" olarak güncellendi!', 'success')

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')

    return redirect(url_for('arac_yonetimi'))

@app.route('/arac-toplu-durum', methods=['POST'])
def arac_toplu_durum():
    """Toplu araç durum güncelle (Aktif/Pasif)"""
    try:
        from database import get_db_connection

        plakalar = request.form.getlist('plakalar')
        aktif = request.form.get('aktif')

        if not plakalar:
            flash('❌ Araç seçilmedi!', 'error')
            return redirect(url_for('arac_yonetimi'))

        conn = get_db_connection()
        cursor = conn.cursor()

        basarili = 0
        for plaka in plakalar:
            cursor.execute('UPDATE araclar SET aktif = ? WHERE plaka = ?', (aktif, plaka))
            basarili += 1

        conn.commit()
        conn.close()

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
    return render_template('kargo_arac_filtre.html')

@app.route('/binek-arac-filtre')
def binek_arac_filtre():
    """Binek araç filtre sayfası"""
    return render_template('binek_arac_filtre.html')

@app.route('/is-makinesi-filtre')
def is_makinesi_filtre():
    """İş makinesi filtre sayfası"""
    return render_template('is_makinesi_filtre.html')

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
        from database import get_aktif_binek_araclar, get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Filtreleri al
        baslangic_tarihi = request.form.get('baslangic_tarihi') if request.method == 'POST' else None
        bitis_tarihi = request.form.get('bitis_tarihi') if request.method == 'POST' else None
        plaka_filtre = request.form.get('plaka') if request.method == 'POST' else None
        dahil_taseron = request.form.get('dahil_taseron') == '1' if request.method == 'POST' else False

        aktif_binek = get_aktif_binek_araclar(dahil_taseron=dahil_taseron)

        if not aktif_binek:
            flash('⚠️ Aktif binek araç bulunamadı. Araç Yönetimi\'nden binek araç ekleyin.', 'warning')
            return render_template('result.html',
                                 arac_detaylari=[],
                                 genel_ozet={'arac_tipi': 'Binek Araç', 'toplam_arac': 0, 'toplam_yakit': 0})

        # SQL sorgusu filtrelerle
        where_conditions = [f'y.plaka IN ({",".join("?" * len(aktif_binek))})']
        params = list(aktif_binek)

        if baslangic_tarihi:
            where_conditions.append('y.islem_tarihi >= ?')
            params.append(baslangic_tarihi)

        if bitis_tarihi:
            where_conditions.append('y.islem_tarihi <= ?')
            params.append(bitis_tarihi)

        if plaka_filtre:
            where_conditions.append('y.plaka = ?')
            params.append(plaka_filtre)

        where_clause = ' AND '.join(where_conditions)

        cursor.execute(f'''
            SELECT
                y.plaka,
                SUM(y.yakit_miktari) as toplam_yakit,
                AVG(y.yakit_miktari) as ortalama_yakit,
                COUNT(*) as yakit_alimlari
            FROM yakit y
            WHERE {where_clause}
            AND y.yakit_miktari IS NOT NULL
            AND y.yakit_miktari > 0
            GROUP BY y.plaka
            ORDER BY toplam_yakit DESC
        ''', tuple(params))

        rows = cursor.fetchall()

        arac_detaylari = []
        toplam_yakit_genel = 0

        from database import hesapla_gercek_km

        for row in rows:
            plaka = row['plaka']
            toplam_yakit = float(row['toplam_yakit'])
            yakit_alimlari = row['yakit_alimlari']

            # DOĞRU KM HESAPLAMA: Ardışık kayıtlar arasındaki fark (TARİH FİLTRELİ)
            toplam_km = hesapla_gercek_km(plaka, conn, baslangic_tarihi, bitis_tarihi)

            tüketim = (toplam_yakit / toplam_km * 100) if toplam_km > 0 else 0

            arac_detaylari.append({
                'plaka': row['plaka'],
                'toplam_yakit': toplam_yakit,
                'toplam_km': toplam_km,
                'ortalama_yakit': float(row['ortalama_yakit']),
                'yakit_alimlari': yakit_alimlari,
                'tuketim_100km': tüketim
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
                             tahminler=tahminler)

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/is-makinesi-analizi', methods=['GET', 'POST'])
def is_makinesi_analizi():
    """İş makinesi analizi sayfası"""
    try:
        from database import get_aktif_is_makineleri, get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

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

        # SQL sorgusu filtrelerle
        where_conditions = [f'y.plaka IN ({",".join("?" * len(aktif_makineler))})']
        params = list(aktif_makineler)

        if baslangic_tarihi:
            where_conditions.append('y.islem_tarihi >= ?')
            params.append(baslangic_tarihi)

        if bitis_tarihi:
            where_conditions.append('y.islem_tarihi <= ?')
            params.append(bitis_tarihi)

        if plaka_filtre:
            where_conditions.append('y.plaka = ?')
            params.append(plaka_filtre)

        where_clause = ' AND '.join(where_conditions)

        cursor.execute(f'''
            SELECT
                y.plaka,
                SUM(y.yakit_miktari) as toplam_yakit,
                AVG(y.yakit_miktari) as ortalama_yakit,
                COUNT(*) as yakit_alimlari
            FROM yakit y
            WHERE {where_clause}
            AND y.yakit_miktari IS NOT NULL
            AND y.yakit_miktari > 0
            GROUP BY y.plaka
            ORDER BY toplam_yakit DESC
        ''', tuple(params))

        rows = cursor.fetchall()

        arac_detaylari = []
        toplam_yakit_genel = 0

        from database import hesapla_gercek_km

        for row in rows:
            plaka = row['plaka']
            toplam_yakit = float(row['toplam_yakit'])
            yakit_alimlari = row['yakit_alimlari']

            # DOĞRU KM HESAPLAMA: Ardışık kayıtlar arasındaki fark (TARİH FİLTRELİ)
            toplam_km = hesapla_gercek_km(plaka, conn, baslangic_tarihi, bitis_tarihi)

            tüketim = (toplam_yakit / toplam_km * 100) if toplam_km > 0 else 0

            arac_detaylari.append({
                'plaka': row['plaka'],
                'toplam_yakit': toplam_yakit,
                'toplam_km': toplam_km,
                'ortalama_yakit': float(row['ortalama_yakit']),
                'yakit_alimlari': yakit_alimlari,
                'tuketim_100km': tüketim
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
                             tahminler=tahminler)

    except Exception as e:
        flash(f'❌ Hata: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Flask Yakıt Tahmin Sistemi Başlatılıyor...")
    print("="*50)
    print("📍 URL: http://localhost:5000")
    print("📁 Veritabanı: kargo_data.db")
    print("🔍 Durum: http://localhost:5000/database-status")
    print("="*50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
