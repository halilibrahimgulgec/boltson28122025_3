import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from database import get_yakit_data, get_arac_takip_data, get_agirlik_data
import pickle
import os
from datetime import datetime, timedelta

class YakitTahminModeli:
    """Yakıt tüketim tahmini için AI modeli"""

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []

    def veri_hazirla(self):
        """Veritabanından veri çek ve özellik mühendisliği yap"""
        yakit_data = get_yakit_data()
        arac_takip_data = get_arac_takip_data()

        if not yakit_data or len(yakit_data) < 10:
            return None, None

        df_yakit = pd.DataFrame(yakit_data)
        df_arac = pd.DataFrame(arac_takip_data) if arac_takip_data else pd.DataFrame()

        # Tarih özelliklerini çıkar
        df_yakit['islem_tarihi'] = pd.to_datetime(df_yakit['islem_tarihi'], errors='coerce')
        df_yakit['gun'] = df_yakit['islem_tarihi'].dt.day
        df_yakit['ay'] = df_yakit['islem_tarihi'].dt.month
        df_yakit['haftanin_gunu'] = df_yakit['islem_tarihi'].dt.dayofweek

        # Plaka bazlı özellikler
        plaka_stats = df_yakit.groupby('plaka').agg({
            'yakit_miktari': ['mean', 'std', 'count'],
            'km_bilgisi': 'mean'
        }).reset_index()

        plaka_stats.columns = ['plaka', 'ort_yakit', 'std_yakit', 'sefer_sayisi', 'ort_km']
        df_yakit = df_yakit.merge(plaka_stats, on='plaka', how='left')

        # Araç takip verisiyle birleştir
        if not df_arac.empty:
            df_arac['tarih'] = pd.to_datetime(df_arac['tarih'], errors='coerce')
            df_arac_grouped = df_arac.groupby('plaka').agg({
                'toplam_kilometre': 'mean',
                'maksimum_hiz': 'mean',
                'gunluk_yakit_tuketimi_l': 'mean'
            }).reset_index()

            df_arac_grouped.columns = ['plaka', 'ort_km_takip', 'ort_max_hiz', 'ort_gunluk_yakit']
            df_yakit = df_yakit.merge(df_arac_grouped, on='plaka', how='left')

        # Eksik değerleri doldur
        df_yakit = df_yakit.fillna(0)

        # Özellikler ve hedef
        feature_cols = ['gun', 'ay', 'haftanin_gunu', 'ort_yakit', 'std_yakit',
                       'sefer_sayisi', 'ort_km']

        if not df_arac.empty:
            feature_cols.extend(['ort_km_takip', 'ort_max_hiz', 'ort_gunluk_yakit'])

        self.feature_names = feature_cols

        # Geçerli satırları filtrele
        df_valid = df_yakit[df_yakit['yakit_miktari'].notna() & (df_yakit['yakit_miktari'] > 0)]

        if len(df_valid) < 10:
            return None, None

        X = df_valid[feature_cols].values
        y = df_valid['yakit_miktari'].values

        return X, y

    def egit(self):
        """Modeli eğit"""
        X, y = self.veri_hazirla()

        if X is None or len(X) < 10:
            return {
                'status': 'error',
                'message': 'Yetersiz veri. En az 10 kayıt gerekli.'
            }

        # Veriyi ölçeklendir
        X_scaled = self.scaler.fit_transform(X)

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # Random Forest modeli
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train, y_train)

        # Model performansı
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)

        # Özellik önemleri
        feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))

        return {
            'status': 'success',
            'train_score': round(train_score, 3),
            'test_score': round(test_score, 3),
            'feature_importance': feature_importance,
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }

    def tahmin_yap(self, plaka, tarih=None):
        """Belirli bir plaka için yakıt tüketimi tahmini yap"""
        if self.model is None:
            egit_result = self.egit()
            if egit_result['status'] == 'error':
                return egit_result

        yakit_data = get_yakit_data()
        df_yakit = pd.DataFrame(yakit_data)

        # Plaka istatistikleri
        plaka_data = df_yakit[df_yakit['plaka'] == plaka]

        if plaka_data.empty:
            return {
                'status': 'error',
                'message': f'Plaka {plaka} için veri bulunamadı'
            }

        # Tarih bilgisi
        if tarih is None:
            tarih = datetime.now()
        else:
            tarih = pd.to_datetime(tarih)

        # Özellikler
        features = {
            'gun': tarih.day,
            'ay': tarih.month,
            'haftanin_gunu': tarih.dayofweek,
            'ort_yakit': plaka_data['yakit_miktari'].mean(),
            'std_yakit': plaka_data['yakit_miktari'].std(),
            'sefer_sayisi': len(plaka_data),
            'ort_km': plaka_data['km_bilgisi'].mean()
        }

        # Araç takip verisi varsa ekle
        arac_takip = get_arac_takip_data()
        if arac_takip:
            df_arac = pd.DataFrame(arac_takip)
            plaka_arac = df_arac[df_arac['plaka'] == plaka]

            if not plaka_arac.empty:
                features['ort_km_takip'] = plaka_arac['toplam_kilometre'].mean()
                features['ort_max_hiz'] = plaka_arac['maksimum_hiz'].mean()
                features['ort_gunluk_yakit'] = plaka_arac['gunluk_yakit_tuketimi_l'].mean()
            else:
                features['ort_km_takip'] = 0
                features['ort_max_hiz'] = 0
                features['ort_gunluk_yakit'] = 0
        else:
            features['ort_km_takip'] = 0
            features['ort_max_hiz'] = 0
            features['ort_gunluk_yakit'] = 0

        # Özellikleri sırala
        X = np.array([[features[col] for col in self.feature_names]])
        X_scaled = self.scaler.transform(X)

        # Tahmin
        tahmin = self.model.predict(X_scaled)[0]

        # Güven aralığı (basit yaklaşım)
        gercek_ort = plaka_data['yakit_miktari'].mean()
        gercek_std = plaka_data['yakit_miktari'].std()

        return {
            'status': 'success',
            'plaka': plaka,
            'tarih': tarih.strftime('%Y-%m-%d'),
            'tahmin': round(tahmin, 2),
            'gercek_ortalama': round(gercek_ort, 2),
            'min_tahmin': round(tahmin - gercek_std, 2),
            'max_tahmin': round(tahmin + gercek_std, 2),
            'features': features
        }

    def gelecek_ay_tahmini(self, plaka):
        """Gelecek 30 gün için tahmin"""
        tahminler = []
        bugun = datetime.now()

        for i in range(30):
            tarih = bugun + timedelta(days=i)
            tahmin = self.tahmin_yap(plaka, tarih)
            if tahmin['status'] == 'success':
                tahminler.append({
                    'gun': i + 1,
                    'tarih': tahmin['tarih'],
                    'tahmin': tahmin['tahmin']
                })

        return {
            'status': 'success',
            'plaka': plaka,
            'tahminler': tahminler,
            'toplam_tahmin': round(sum(t['tahmin'] for t in tahminler), 2)
        }


class AnomalTespitModeli:
    """Anormal yakıt tüketimi tespiti için AI modeli"""

    def __init__(self):
        self.model = IsolationForest(
            contamination=0.1,  # %10 anomali bekliyoruz
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.egitildi = False

    def egit(self):
        """Modeli eğit"""
        yakit_data = get_yakit_data()

        if not yakit_data or len(yakit_data) < 20:
            return {
                'status': 'error',
                'message': 'Yetersiz veri. En az 20 kayıt gerekli.'
            }

        df = pd.DataFrame(yakit_data)

        # Özellikler: yakıt miktarı, km bilgisi, birim fiyat
        features = []
        valid_indices = []

        for idx, row in df.iterrows():
            yakit = row.get('yakit_miktari')
            km = row.get('km_bilgisi')
            fiyat = row.get('birim_fiyat')

            if yakit and yakit > 0:
                features.append([
                    float(yakit),
                    float(km) if km else 0,
                    float(fiyat) if fiyat else 0
                ])
                valid_indices.append(idx)

        if len(features) < 20:
            return {
                'status': 'error',
                'message': 'Geçerli veri yetersiz'
            }

        X = np.array(features)
        X_scaled = self.scaler.fit_transform(X)

        # Modeli eğit
        self.model.fit(X_scaled)
        self.egitildi = True

        # Anomalileri tespit et
        predictions = self.model.predict(X_scaled)
        anomaly_count = (predictions == -1).sum()

        return {
            'status': 'success',
            'total_samples': len(features),
            'anomaly_count': int(anomaly_count),
            'anomaly_percentage': round(anomaly_count / len(features) * 100, 2)
        }

    def anomali_tespit(self):
        """Tüm verilerde anomali tespit et"""
        if not self.egitildi:
            egit_result = self.egit()
            if egit_result['status'] == 'error':
                return egit_result

        yakit_data = get_yakit_data()
        df = pd.DataFrame(yakit_data)

        anomaliler = []

        for idx, row in df.iterrows():
            yakit = row.get('yakit_miktari')
            km = row.get('km_bilgisi')
            fiyat = row.get('birim_fiyat')

            if yakit and yakit > 0:
                X = np.array([[
                    float(yakit),
                    float(km) if km else 0,
                    float(fiyat) if fiyat else 0
                ]])
                X_scaled = self.scaler.transform(X)

                prediction = self.model.predict(X_scaled)[0]
                score = self.model.score_samples(X_scaled)[0]

                if prediction == -1:
                    anomaliler.append({
                        'plaka': row.get('plaka'),
                        'tarih': row.get('islem_tarihi'),
                        'yakit_miktari': float(yakit),
                        'km_bilgisi': float(km) if km else 0,
                        'birim_fiyat': float(fiyat) if fiyat else 0,
                        'anomali_skoru': round(float(score), 3),
                        'sebep': self._anomali_sebebi(row)
                    })

        # En kötü 20 anomaliyi döndür
        anomaliler.sort(key=lambda x: x['anomali_skoru'])

        return {
            'status': 'success',
            'toplam_anomali': len(anomaliler),
            'anomaliler': anomaliler[:20]
        }

    def anomali_tespit_detayli(self, plaka_filtre=None, tip_filtre=None, baslangic_tarihi=None, bitis_tarihi=None):
        """Dashboard için detaylı anomali analizi - filtreleme destekli"""
        if not self.egitildi:
            egit_result = self.egit()
            if egit_result['status'] == 'error':
                return egit_result

        yakit_data = get_yakit_data()
        df = pd.DataFrame(yakit_data)

        # Tarih filtreleme için tarihleri datetime'a çevir
        if baslangic_tarihi or bitis_tarihi:
            df['islem_tarihi_dt'] = pd.to_datetime(df['islem_tarihi'], errors='coerce')

        anomaliler = []
        plaka_anomali_sayisi = {}
        anomali_tipleri = {
            'asiri_yuksek': 0,
            'asiri_dusuk': 0,
            'eksik_km': 0,
            'anormal_fiyat': 0
        }

        for idx, row in df.iterrows():
            yakit = row.get('yakit_miktari')
            km = row.get('km_bilgisi')
            fiyat = row.get('birim_fiyat')
            plaka = row.get('plaka')

            if yakit and yakit > 0:
                X = np.array([[
                    float(yakit),
                    float(km) if km else 0,
                    float(fiyat) if fiyat else 0
                ]])
                X_scaled = self.scaler.transform(X)

                prediction = self.model.predict(X_scaled)[0]
                score = self.model.score_samples(X_scaled)[0]

                if prediction == -1:
                    sebep_data = self._anomali_sebep_analiz(row)

                    # Filtreleme kontrolü
                    anomali_gecerli = True

                    # Plaka filtresi
                    if plaka_filtre and plaka != plaka_filtre:
                        anomali_gecerli = False

                    # Tip filtresi
                    if tip_filtre and sebep_data['tip'] != tip_filtre:
                        anomali_gecerli = False

                    # Tarih filtresi
                    if baslangic_tarihi or bitis_tarihi:
                        tarih_dt = row.get('islem_tarihi_dt')
                        if pd.notna(tarih_dt):
                            if baslangic_tarihi:
                                baslangic_dt = pd.to_datetime(baslangic_tarihi)
                                if tarih_dt < baslangic_dt:
                                    anomali_gecerli = False
                            if bitis_tarihi:
                                bitis_dt = pd.to_datetime(bitis_tarihi)
                                if tarih_dt > bitis_dt:
                                    anomali_gecerli = False

                    if anomali_gecerli:
                        anomali = {
                            'plaka': plaka,
                            'tarih': row.get('islem_tarihi'),
                            'yakit_miktari': float(yakit),
                            'km_bilgisi': float(km) if km else 0,
                            'birim_fiyat': float(fiyat) if fiyat else 0,
                            'anomali_skoru': round(float(score), 3),
                            'sebep': sebep_data['sebep_text'],
                            'tip': sebep_data['tip']
                        }
                        anomaliler.append(anomali)

                        # Plaka bazlı sayım
                        if plaka not in plaka_anomali_sayisi:
                            plaka_anomali_sayisi[plaka] = 0
                        plaka_anomali_sayisi[plaka] += 1

                        # Tip bazlı sayım
                        if sebep_data['tip']:
                            anomali_tipleri[sebep_data['tip']] += 1

        # Anomalileri skora göre sırala
        anomaliler.sort(key=lambda x: x['anomali_skoru'])

        # En çok anomalisi olan 10 plakayı bul
        top_anomali_plakalar = sorted(
            plaka_anomali_sayisi.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Tarih bazlı dağılım
        df_anomali = pd.DataFrame(anomaliler)
        if not df_anomali.empty:
            df_anomali['tarih'] = pd.to_datetime(df_anomali['tarih'], errors='coerce')
            df_anomali['ay_yil'] = df_anomali['tarih'].dt.strftime('%Y-%m')
            tarih_dagilim = df_anomali['ay_yil'].value_counts().to_dict()
        else:
            tarih_dagilim = {}

        return {
            'status': 'success',
            'toplam_anomali': len(anomaliler),
            'anomaliler': anomaliler,
            'plaka_anomali_sayisi': dict(plaka_anomali_sayisi),
            'top_anomali_plakalar': top_anomali_plakalar,
            'anomali_tipleri': anomali_tipleri,
            'tarih_dagilim': tarih_dagilim
        }

    def _anomali_sebebi(self, row):
        """Anomalinin muhtemel sebebini belirle"""
        yakit = row.get('yakit_miktari', 0)
        km = row.get('km_bilgisi', 0)
        fiyat = row.get('birim_fiyat', 0)
        plaka = row.get('plaka', '')

        sebepler = []
        detaylar = []

        # Ortalamaları hesapla
        yakit_data = get_yakit_data()
        df = pd.DataFrame(yakit_data)

        ort_yakit = df['yakit_miktari'].mean()
        std_yakit = df['yakit_miktari'].std()
        ort_fiyat = df['birim_fiyat'].mean()

        # Plaka bazlı ortalamalar
        plaka_df = df[df['plaka'] == plaka]
        if not plaka_df.empty:
            plaka_ort_yakit = plaka_df['yakit_miktari'].mean()
        else:
            plaka_ort_yakit = ort_yakit

        # 1. AŞIRI YÜKSEK YAKIT TÜKETİMİ (KRİTİK)
        if yakit > ort_yakit * 2:
            fark = yakit - ort_yakit
            sebepler.append('🔴 AŞIRI YÜKSEK YAKIT TÜKETİMİ')
            detaylar.append(f'Normal: {ort_yakit:.1f}L, Gerçek: {yakit:.1f}L (+{fark:.1f}L fark)')
        elif yakit > ort_yakit * 1.5:
            fark = yakit - ort_yakit
            sebepler.append('🟡 Yüksek yakıt tüketimi')
            detaylar.append(f'Normal: {ort_yakit:.1f}L, Gerçek: {yakit:.1f}L (+{fark:.1f}L fark)')

        # 2. BEKLENENDEN DÜŞÜK TÜKETİM (ŞÜPHELI)
        if yakit < ort_yakit * 0.3:
            fark = ort_yakit - yakit
            sebepler.append('🔴 BEKLENENDEN ÇOK DÜŞÜK TÜKETİM')
            detaylar.append(f'Normal: {ort_yakit:.1f}L, Gerçek: {yakit:.1f}L (-{fark:.1f}L fark)')
        elif yakit < ort_yakit * 0.5:
            fark = ort_yakit - yakit
            sebepler.append('🟡 Düşük tüketim')
            detaylar.append(f'Normal: {ort_yakit:.1f}L, Gerçek: {yakit:.1f}L (-{fark:.1f}L fark)')

        # 3. EKSİK KM BİLGİSİ (KRİTİK)
        if not km or km == 0:
            sebepler.append('🔴 EKSİK KM BİLGİSİ')
            detaylar.append('Kilometre bilgisi girilmemiş - tüketim hesaplanamıyor')
        elif km < 10:
            sebepler.append('🟡 Şüpheli KM bilgisi')
            detaylar.append(f'KM çok düşük: {km}km')

        # Anormal fiyat (ek kontrol)
        if fiyat and ort_fiyat and abs(fiyat - ort_fiyat) > ort_fiyat * 0.3:
            fark = abs(fiyat - ort_fiyat)
            sebepler.append('⚠️ Anormal fiyat')
            detaylar.append(f'Normal: {ort_fiyat:.2f}₺/L, Gerçek: {fiyat:.2f}₺/L')

        sebep_text = ' | '.join(sebepler) if sebepler else 'Genel anomali'
        detay_text = ' | '.join(detaylar) if detaylar else ''

        return f"{sebep_text}\n{detay_text}" if detay_text else sebep_text

    def _anomali_sebep_analiz(self, row):
        """Anomalinin sebebini ve tipini belirle (dashboard için)"""
        yakit = row.get('yakit_miktari', 0)
        km = row.get('km_bilgisi', 0)
        fiyat = row.get('birim_fiyat', 0)
        plaka = row.get('plaka', '')

        yakit_data = get_yakit_data()
        df = pd.DataFrame(yakit_data)
        ort_yakit = df['yakit_miktari'].mean()
        ort_fiyat = df['birim_fiyat'].mean()

        tip = None
        sebep_text = self._anomali_sebebi(row)

        # Anomali tipini belirle
        if yakit > ort_yakit * 1.5:
            tip = 'asiri_yuksek'
        elif yakit < ort_yakit * 0.5:
            tip = 'asiri_dusuk'
        elif not km or km == 0:
            tip = 'eksik_km'
        elif fiyat and ort_fiyat and abs(fiyat - ort_fiyat) > ort_fiyat * 0.3:
            tip = 'anormal_fiyat'

        return {
            'sebep_text': sebep_text,
            'tip': tip
        }


class PerformansAnalizi:
    """Araç performans analizi - Yakıt/KM oranı ve tonaj"""

    def __init__(self):
        self.yakit_data = None
        self.agirlik_data = None

    def veri_yukle(self):
        """Verileri yükle"""
        self.yakit_data = pd.DataFrame(get_yakit_data())
        self.agirlik_data = pd.DataFrame(get_agirlik_data())

        if not self.yakit_data.empty:
            self.yakit_data['islem_tarihi'] = pd.to_datetime(self.yakit_data['islem_tarihi'], errors='coerce')

        if not self.agirlik_data.empty:
            self.agirlik_data['tarih'] = pd.to_datetime(self.agirlik_data['tarih'], errors='coerce')

    def plaka_performans_karsilastirma(self, ana_malzeme_filtre=None, arac_tipi_filtre=None):
        """Tüm plakaların performansını karşılaştır"""
        if self.yakit_data is None:
            self.veri_yukle()

        if self.yakit_data.empty:
            return {
                'status': 'error',
                'message': 'Yakıt verisi bulunamadı'
            }

        # Plaka bazlı yakıt ve KM bilgileri
        yakit_stats = self.yakit_data.groupby('plaka').agg({
            'yakit_miktari': 'sum',
            'km_bilgisi': 'sum',
            'satir_tutari': 'sum'
        }).reset_index()

        # Plaka bazlı tonaj ve ANA MALZEME bilgileri
        if not self.agirlik_data.empty:
            # miktar sütununu numeric'e çevir
            self.agirlik_data['miktar'] = pd.to_numeric(self.agirlik_data['miktar'], errors='coerce')

            # Sadece miktar > 0 ve birim = 'Kg' olanları al
            agirlik_filtered = self.agirlik_data[
                (self.agirlik_data['miktar'].notna()) &
                (self.agirlik_data['miktar'] > 0) &
                (self.agirlik_data['birim'] == 'Kg')
            ].copy()

            tonaj_stats = agirlik_filtered.groupby('plaka').agg({
                'miktar': 'sum',
                'ana_malzeme': 'first'
            }).reset_index()
            tonaj_stats.columns = ['plaka', 'toplam_tonaj', 'ana_malzeme']
        else:
            tonaj_stats = pd.DataFrame(columns=['plaka', 'toplam_tonaj', 'ana_malzeme'])

        # Birleştir
        performans = yakit_stats.merge(tonaj_stats, on='plaka', how='left')
        performans['toplam_tonaj'] = performans['toplam_tonaj'].fillna(0)
        performans['ana_malzeme'] = performans['ana_malzeme'].fillna('Bilinmiyor')

        # Araç tipi bilgisini araclar tablosundan ekle
        from database import fetch_all_paginated
        araclar_data = fetch_all_paginated('araclar', select='plaka,arac_tipi')
        araclar_df = pd.DataFrame(araclar_data)

        performans = performans.merge(araclar_df, on='plaka', how='left')
        performans['arac_tipi'] = performans['arac_tipi'].fillna('KARGO ARACI')

        # ARAÇ TİPİ FİLTRESİ UYGULA (ÇOK ÖNEMLİ!)
        if arac_tipi_filtre and arac_tipi_filtre.strip():
            performans = performans[performans['arac_tipi'] == arac_tipi_filtre]

            # Eğer hiç araç yoksa
            if performans.empty:
                return {
                    'status': 'error',
                    'message': f'{arac_tipi_filtre} tipinde araç bulunamadı'
                }

        # ANA MALZEME FİLTRESİ (sadece KARGO ARAÇLARI için)
        if ana_malzeme_filtre and ana_malzeme_filtre.strip():
            performans = performans[
                (performans['arac_tipi'] == 'KARGO ARACI') &
                (performans['ana_malzeme'] == ana_malzeme_filtre)
            ]

            # Eğer hiç araç yoksa
            if performans.empty:
                return {
                    'status': 'error',
                    'message': f'{ana_malzeme_filtre} malzemesi taşıyan kargo aracı bulunamadı'
                }

        # GEÇERSİZ VERİLERİ FİLTRELE (0 yakıt veya 0 km olanlar)
        performans = performans[
            (performans['yakit_miktari'] > 0) &
            (performans['km_bilgisi'] > 0)
        ]

        # Eğer hiç geçerli veri yoksa
        if performans.empty:
            return {
                'status': 'error',
                'message': 'Seçili kriterlerde geçerli veri bulunamadı (yakıt ve km verisi olan araç yok)'
            }

        # Hesaplamalar
        performans['km_litre_orani'] = performans.apply(
            lambda row: round(row['km_bilgisi'] / row['yakit_miktari'], 2)
            if row['yakit_miktari'] > 0 else 0, axis=1
        )

        # ANORMAL YÜKSEK KM/L ORANLARINI FİLTRELE (büyük ihtimalle hatalı veri)
        # Kamyonlar için maksimum 50 km/L, iş makineleri için 30 km/L, binek için 100 km/L mantıklı
        if arac_tipi_filtre == 'KARGO ARACI':
            max_km_litre = 50
        elif arac_tipi_filtre == 'İŞ MAKİNESİ':
            max_km_litre = 30
        elif arac_tipi_filtre == 'BİNEK ARAÇ':
            max_km_litre = 100
        else:
            max_km_litre = 100

        performans = performans[performans['km_litre_orani'] <= max_km_litre]

        # Eğer filtrelemeden sonra veri kalmadıysa
        if performans.empty:
            return {
                'status': 'error',
                'message': 'Geçerli veri bulunamadı (tüm veriler anormal yüksek veya düşük değerlere sahip)'
            }

        performans['km_basina_maliyet'] = performans.apply(
            lambda row: round(row['satir_tutari'] / row['km_bilgisi'], 2)
            if row['km_bilgisi'] > 0 else 0, axis=1
        )

        performans['ton_basina_yakit'] = performans.apply(
            lambda row: round((row['toplam_tonaj'] / 1000) / row['yakit_miktari'], 2)
            if row['yakit_miktari'] > 0 else 0, axis=1
        )

        # Verimlilik skoru (yüksek = iyi, ters çevir)
        performans['verimlilik_skoru'] = performans.apply(
            lambda row: round(100 / row['km_litre_orani'], 2) if row['km_litre_orani'] > 0 else 999,
            axis=1
        )

        # Sıralama
        performans = performans.sort_values('verimlilik_skoru', ascending=False)

        # En iyi ve en kötü araçlar
        en_verimli = performans.nsmallest(5, 'verimlilik_skoru').to_dict('records')
        en_verimsiz = performans.nlargest(5, 'verimlilik_skoru').to_dict('records')

        veriler = []
        for _, row in performans.iterrows():
            veri = {
                'plaka': row['plaka'],
                'arac_tipi': row['arac_tipi'],
                'toplam_yakit': round(row['yakit_miktari'], 1),
                'toplam_km': round(row['km_bilgisi'], 0),
                'km_litre': round(row['km_litre_orani'], 2) if row['km_litre_orani'] > 0 else None,
                'km_maliyet': round(row['km_basina_maliyet'], 2) if row['km_basina_maliyet'] > 0 else None,
                'verimlilik': 'İyi' if row['km_litre_orani'] > performans['km_litre_orani'].mean() else 'Kötü'
            }

            # KARGO ARACI ise ana malzeme ve tonaj ekle
            if row['arac_tipi'] == 'KARGO ARACI':
                veri['ana_malzeme'] = row['ana_malzeme']
                veri['toplam_tonaj'] = round(row['toplam_tonaj'] / 1000, 2)
                veri['ton_yakit'] = round(row['ton_basina_yakit'], 2) if row['ton_basina_yakit'] > 0 else None
            else:
                veri['ana_malzeme'] = row['arac_tipi']
                veri['toplam_tonaj'] = None
                veri['ton_yakit'] = None

            veriler.append(veri)

        return {
            'status': 'success',
            'tum_araclar': performans.to_dict('records'),
            'en_verimli': en_verimli,
            'en_verimsiz': en_verimsiz,
            'ortalama_km_litre': round(performans['km_litre_orani'].mean(), 2),
            'ortalama_km_maliyet': round(performans['km_basina_maliyet'].mean(), 2),
            'ortalama_ton_yakit': round(performans['ton_basina_yakit'].mean(), 2) if len(performans) > 0 else 0,
            'toplam_arac': len(performans),
            'veriler': veriler
        }

    def plaka_detay_analiz(self, plaka, baslangic_tarihi=None, bitis_tarihi=None):
        """Belirli bir plaka için detaylı analiz"""
        if self.yakit_data is None:
            self.veri_yukle()

        # Plaka filtreleme
        yakit_plaka = self.yakit_data[self.yakit_data['plaka'] == plaka].copy()
        agirlik_plaka = self.agirlik_data[self.agirlik_data['plaka'] == plaka].copy() if not self.agirlik_data.empty else pd.DataFrame()

        # Tarih filtreleme
        if baslangic_tarihi and bitis_tarihi:
            baslangic = pd.to_datetime(baslangic_tarihi)
            bitis = pd.to_datetime(bitis_tarihi)
            yakit_plaka = yakit_plaka[(yakit_plaka['islem_tarihi'] >= baslangic) &
                                      (yakit_plaka['islem_tarihi'] <= bitis)]
            if not agirlik_plaka.empty:
                agirlik_plaka = agirlik_plaka[(agirlik_plaka['tarih'] >= baslangic) &
                                              (agirlik_plaka['tarih'] <= bitis)]

        if yakit_plaka.empty:
            return {
                'status': 'error',
                'message': f'Plaka {plaka} için belirtilen tarih aralığında veri bulunamadı'
            }

        # Hesaplamalar
        toplam_yakit = yakit_plaka['yakit_miktari'].sum()
        toplam_km = yakit_plaka['km_bilgisi'].sum()
        toplam_maliyet = yakit_plaka['satir_tutari'].sum()
        sefer_sayisi = len(yakit_plaka)

        # miktar sütununu numeric'e çevir
        agirlik_plaka['miktar'] = pd.to_numeric(agirlik_plaka['miktar'], errors='coerce')

        # Sadece miktar > 0 ve birim = 'Kg' olanları al
        agirlik_filtered = agirlik_plaka[
            (agirlik_plaka['miktar'].notna()) &
            (agirlik_plaka['miktar'] > 0) &
            (agirlik_plaka['birim'] == 'Kg')
        ]
        toplam_tonaj = agirlik_filtered['miktar'].sum() if not agirlik_filtered.empty else 0
        yuklenme_sayisi = len(agirlik_plaka) if not agirlik_plaka.empty else 0

        km_litre_orani = toplam_km / toplam_yakit if toplam_yakit > 0 else 0
        km_basina_maliyet = toplam_maliyet / toplam_km if toplam_km > 0 else 0
        # Ton/Yakıt oranı (litre başına kaç ton taşındı)
        toplam_tonaj_ton = toplam_tonaj / 1000
        ton_basina_yakit = toplam_tonaj_ton / toplam_yakit if toplam_yakit > 0 else 0

        # Aylık trend
        yakit_plaka['ay_yil'] = yakit_plaka['islem_tarihi'].dt.strftime('%Y-%m')
        aylik_yakit = yakit_plaka.groupby('ay_yil')['yakit_miktari'].sum().to_dict()
        aylik_km = yakit_plaka.groupby('ay_yil')['km_bilgisi'].sum().to_dict()

        return {
            'status': 'success',
            'plaka': plaka,
            'tarih_araligi': f"{baslangic_tarihi or 'Başlangıç'} - {bitis_tarihi or 'Bugün'}",
            'ozet': {
                'toplam_yakit': round(toplam_yakit, 2),
                'toplam_km': round(toplam_km, 2),
                'toplam_maliyet': round(toplam_maliyet, 2),
                'sefer_sayisi': sefer_sayisi,
                'toplam_tonaj': round(toplam_tonaj, 2),
                'yuklenme_sayisi': yuklenme_sayisi
            },
            'performans': {
                'km_litre_orani': round(km_litre_orani, 2),
                'km_basina_maliyet': round(km_basina_maliyet, 2),
                'ton_basina_yakit': round(ton_basina_yakit, 2),
                'verimlilik_skoru': round(100 / km_litre_orani, 2) if km_litre_orani > 0 else 999
            },
            'trend': {
                'aylik_yakit': aylik_yakit,
                'aylik_km': aylik_km
            }
        }


def tum_plakalar_tahmini():
    """Tüm plakalar için toplu tahmin"""
    from database import get_all_plakas

    plakalar = get_all_plakas()
    model = YakitTahminModeli()

    # Modeli bir kez eğit
    egit_result = model.egit()
    if egit_result['status'] == 'error':
        return egit_result

    sonuclar = []

    for plaka in plakalar[:20]:  # İlk 20 plaka
        tahmin = model.gelecek_ay_tahmini(plaka)
        if tahmin['status'] == 'success':
            sonuclar.append({
                'plaka': plaka,
                'gelecek_ay_toplam': tahmin['toplam_tahmin']
            })

    return {
        'status': 'success',
        'model_performansi': egit_result,
        'plaka_tahminleri': sonuclar,
        'toplam_tahmin': round(sum(s['gelecek_ay_toplam'] for s in sonuclar), 2)
    }
