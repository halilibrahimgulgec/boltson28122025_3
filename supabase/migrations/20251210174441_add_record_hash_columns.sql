/*
  # Duplicate Kontrol Kolonu Ekle

  1. Değişiklikler
    - `yakit` tablosuna `record_hash` kolonu eklenir
    - `agirlik` tablosuna `record_hash` kolonu eklenir
    - `arac_takip` tablosuna `record_hash` kolonu eklenir
    
  2. Amaç
    - Aynı kayıt tekrar eklenmesini önlemek
    - Her gün yeni veriler eklenebilir
    - Eski veriler silinmez
    
  3. Güvenlik
    - Mevcut veriler etkilenmez
    - Sadece yeni kolon eklenir
*/

-- Yakıt tablosuna record_hash ekle
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'yakit' AND column_name = 'record_hash'
  ) THEN
    ALTER TABLE yakit ADD COLUMN record_hash TEXT;
    CREATE INDEX IF NOT EXISTS idx_yakit_record_hash ON yakit(record_hash);
  END IF;
END $$;

-- Ağırlık tablosuna record_hash ekle
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'agirlik' AND column_name = 'record_hash'
  ) THEN
    ALTER TABLE agirlik ADD COLUMN record_hash TEXT;
    CREATE INDEX IF NOT EXISTS idx_agirlik_record_hash ON agirlik(record_hash);
  END IF;
END $$;

-- Araç takip tablosuna record_hash ekle
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'arac_takip' AND column_name = 'record_hash'
  ) THEN
    ALTER TABLE arac_takip ADD COLUMN record_hash TEXT;
    CREATE INDEX IF NOT EXISTS idx_arac_takip_record_hash ON arac_takip(record_hash);
  END IF;
END $$;
