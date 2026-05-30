-- Fill every missing store price by deriving from whatever price already exists
-- Step 1: ensure every product has a Biedronka price (derive from other stores)
-- Step 2: propagate Biedronka to every store still missing a price
-- Safe: ON CONFLICT DO NOTHING never overwrites real prices

DO $$
DECLARE
  bid INT; lid INT; kauf INT; aldi_id INT; netto INT; auch INT; carr INT;
BEGIN
  SELECT id INTO bid     FROM stores WHERE name = 'Biedronka';
  SELECT id INTO lid     FROM stores WHERE name = 'Lidl';
  SELECT id INTO kauf    FROM stores WHERE name = 'Kaufland';
  SELECT id INTO aldi_id FROM stores WHERE name = 'Aldi';
  SELECT id INTO netto   FROM stores WHERE name = 'Netto';
  SELECT id INTO auch    FROM stores WHERE name = 'Auchan';
  SELECT id INTO carr    FROM stores WHERE name = 'Carrefour';

  -- Step 1: give every product a Biedronka price if missing
  -- Derives from Aldi→Lidl→Netto→any store, or falls back to 4.99
  INSERT INTO prices (product_id, store_id, price)
  SELECT p.id, bid,
    COALESCE(
      (SELECT ROUND(CAST(pr.price / 0.920 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = aldi_id LIMIT 1),
      (SELECT ROUND(CAST(pr.price / 0.940 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = lid LIMIT 1),
      (SELECT ROUND(CAST(pr.price / 0.970 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = netto LIMIT 1),
      (SELECT ROUND(CAST(pr.price / 1.060 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = kauf LIMIT 1),
      (SELECT ROUND(CAST(pr.price / 1.090 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = auch LIMIT 1),
      (SELECT ROUND(CAST(pr.price / 1.130 AS NUMERIC), 2) FROM prices pr WHERE pr.product_id = p.id AND pr.store_id = carr LIMIT 1),
      4.99
    )
  FROM products p
  WHERE NOT EXISTS (SELECT 1 FROM prices WHERE product_id = p.id AND store_id = bid)
  ON CONFLICT (product_id, store_id) DO NOTHING;

  -- Step 2: propagate Biedronka to every store still missing a price
  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, aldi_id, ROUND(CAST(price * 0.920 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, lid, ROUND(CAST(price * 0.940 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, netto, ROUND(CAST(price * 0.970 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, kauf, ROUND(CAST(price * 1.060 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, auch, ROUND(CAST(price * 1.090 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

  INSERT INTO prices (product_id, store_id, price)
    SELECT product_id, carr, ROUND(CAST(price * 1.130 AS NUMERIC), 2)
    FROM prices WHERE store_id = bid
  ON CONFLICT (product_id, store_id) DO NOTHING;

END $$;

-- How many prices per store (all should equal total products)
SELECT s.name, COUNT(*) AS prices,
  (SELECT COUNT(*) FROM products) - COUNT(*) AS still_missing
FROM prices pr
JOIN stores s ON s.id = pr.store_id
GROUP BY s.name ORDER BY s.name;
