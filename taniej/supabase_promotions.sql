-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS promotions (
  id SERIAL PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
  store_id INTEGER REFERENCES stores(id) ON DELETE CASCADE,
  promo_price DECIMAL(10,2) NOT NULL,
  promo_label TEXT,           -- e.g. "-20%", "2+1", "Okazja tygodnia"
  valid_from DATE DEFAULT CURRENT_DATE,
  valid_until DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, product_id)
);

ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read promotions" ON promotions FOR SELECT USING (true);

-- Index for fast lookup of active promotions
CREATE INDEX IF NOT EXISTS idx_promotions_active
  ON promotions(store_id, product_id, valid_until);
