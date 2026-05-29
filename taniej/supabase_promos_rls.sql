-- Allow public (anon) reads on promotions table
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow public read promotions"
  ON promotions FOR SELECT
  USING (true);
