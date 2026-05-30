-- Migration v2: add fingerprint column for duplicate detection.
-- Run ONCE in Supabase SQL Editor (after supabase_receipt_scans.sql).

ALTER TABLE receipt_scans
  ADD COLUMN IF NOT EXISTS fingerprint TEXT;

CREATE INDEX IF NOT EXISTS idx_receipt_scans_fingerprint
  ON receipt_scans(fingerprint)
  WHERE fingerprint IS NOT NULL;

-- Verification
SELECT column_name FROM information_schema.columns
  WHERE table_name = 'receipt_scans' AND column_name = 'fingerprint';
