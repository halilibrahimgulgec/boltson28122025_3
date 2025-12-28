/*
  # Araçlar Tablosu

  1. Yeni Tablolar
    - `araclar`
      - `id` (uuid, primary key)
      - `plaka` (text, unique, not null) - Araç plakası
      - `sahip` (text) - BİZİM veya TAŞERON
      - `arac_tipi` (text) - KARGO ARACI, BİNEK ARAÇ, İŞ MAKİNESİ
      - `aktif` (integer, default 1) - 1: Aktif, 0: Pasif
      - `notlar` (text) - Ek bilgiler
      - `created_at` (timestamptz)

  2. Güvenlik
    - RLS aktif
    - Authenticated kullanıcılar okuyabilir
*/

CREATE TABLE IF NOT EXISTS araclar (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plaka text UNIQUE NOT NULL,
  sahip text DEFAULT 'BİZİM',
  arac_tipi text DEFAULT 'KARGO ARACI',
  aktif integer DEFAULT 1,
  notlar text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE araclar ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read araclar"
  ON araclar
  FOR SELECT
  USING (true);

CREATE POLICY "Anyone can insert araclar"
  ON araclar
  FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Anyone can update araclar"
  ON araclar
  FOR UPDATE
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Anyone can delete araclar"
  ON araclar
  FOR DELETE
  USING (true);
