-- Supabase Veritabanı Şeması
-- Supabase SQL Editor'da çalıştırın

-- 1. Yakıt Tablosu
CREATE TABLE IF NOT EXISTS yakit (
    id BIGSERIAL PRIMARY KEY,
    plaka TEXT,
    yakit_miktari NUMERIC,
    satir_tutari NUMERIC,
    islem_tarihi DATE,
    km_bilgisi NUMERIC,
    birim_fiyat NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Ağırlık Tablosu
CREATE TABLE IF NOT EXISTS agirlik (
    id BIGSERIAL PRIMARY KEY,
    plaka TEXT,
    miktar NUMERIC,
    net_agirlik NUMERIC,
    tarih DATE,
    birim TEXT,
    ana_malzeme TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Araçlar Tablosu
CREATE TABLE IF NOT EXISTS araclar (
    plaka TEXT PRIMARY KEY,
    sahip TEXT DEFAULT 'BİZİM',
    arac_tipi TEXT DEFAULT 'KARGO ARACI',
    aktif INTEGER DEFAULT 1,
    notlar TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Araç Takip Tablosu
CREATE TABLE IF NOT EXISTS arac_takip (
    id BIGSERIAL PRIMARY KEY,
    plaka TEXT,
    tarih DATE,
    konum TEXT,
    durum TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. İşlenen Dosyalar Tablosu (Opsiyonel)
CREATE TABLE IF NOT EXISTS processed_files (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT,
    table_name TEXT,
    record_count INTEGER,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- İndeksler (Performans için)
CREATE INDEX IF NOT EXISTS idx_yakit_plaka ON yakit(plaka);
CREATE INDEX IF NOT EXISTS idx_yakit_tarih ON yakit(islem_tarihi);
CREATE INDEX IF NOT EXISTS idx_agirlik_plaka ON agirlik(plaka);
CREATE INDEX IF NOT EXISTS idx_agirlik_tarih ON agirlik(tarih);
CREATE INDEX IF NOT EXISTS idx_araclar_tipi ON araclar(arac_tipi);
CREATE INDEX IF NOT EXISTS idx_araclar_aktif ON araclar(aktif);

-- Row Level Security (RLS) - Herkese okuma izni
ALTER TABLE yakit ENABLE ROW LEVEL SECURITY;
ALTER TABLE agirlik ENABLE ROW LEVEL SECURITY;
ALTER TABLE araclar ENABLE ROW LEVEL SECURITY;
ALTER TABLE arac_takip ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_files ENABLE ROW LEVEL SECURITY;

-- Public okuma politikaları
CREATE POLICY "Public read yakit" ON yakit FOR SELECT USING (true);
CREATE POLICY "Public read agirlik" ON agirlik FOR SELECT USING (true);
CREATE POLICY "Public read araclar" ON araclar FOR SELECT USING (true);
CREATE POLICY "Public read arac_takip" ON arac_takip FOR SELECT USING (true);
CREATE POLICY "Public read processed_files" ON processed_files FOR SELECT USING (true);

-- Public yazma politikaları (gerekirse)
CREATE POLICY "Public insert yakit" ON yakit FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert agirlik" ON agirlik FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert araclar" ON araclar FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert arac_takip" ON arac_takip FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert processed_files" ON processed_files FOR INSERT WITH CHECK (true);

CREATE POLICY "Public update araclar" ON araclar FOR UPDATE USING (true);
CREATE POLICY "Public delete araclar" ON araclar FOR DELETE USING (true);
