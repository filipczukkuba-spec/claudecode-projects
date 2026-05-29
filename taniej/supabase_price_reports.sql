-- User-submitted shelf prices
CREATE TABLE IF NOT EXISTS price_reports (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  store_id BIGINT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  price DECIMAL(10,2) NOT NULL,
  city TEXT,
  submitted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_reports_product_store ON price_reports(product_id, store_id);
CREATE INDEX IF NOT EXISTS idx_price_reports_submitted ON price_reports(submitted_at DESC);

-- Public read + insert (no update/delete for anon)
ALTER TABLE price_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anyone can read reports"
  ON price_reports FOR SELECT USING (true);

CREATE POLICY "anyone can submit a report"
  ON price_reports FOR INSERT WITH CHECK (price > 0 AND price < 10000);
