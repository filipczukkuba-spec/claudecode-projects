-- Migration v3: add NIP + receipt number for bulletproof duplicate detection.
-- Polish fiscal receipts (paragony) always have:
--   - NIP: 10-digit tax ID of the store (printed in the header)
--   - NR: unique receipt number per store per day
-- Combining (NIP, receipt_number, receipt_date) is globally unique — no two
-- legitimate receipts in Poland will ever share all three.
--
-- Run ONCE in Supabase SQL Editor after v1 and v2.

ALTER TABLE receipt_scans
  ADD COLUMN IF NOT EXISTS store_nip       TEXT,
  ADD COLUMN IF NOT EXISTS receipt_number  TEXT;

-- Composite index for fast dedup lookups
CREATE INDEX IF NOT EXISTS idx_receipt_scans_nip_nr
  ON receipt_scans(store_nip, receipt_number, receipt_date)
  WHERE store_nip IS NOT NULL AND receipt_number IS NOT NULL;

-- Verification
SELECT column_name FROM information_schema.columns
  WHERE table_name = 'receipt_scans'
  AND column_name IN ('store_nip', 'receipt_number');
