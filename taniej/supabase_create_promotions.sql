-- Create promotions table if it doesn't exist, then insert current week promos

CREATE TABLE IF NOT EXISTS promotions (
  id BIGSERIAL PRIMARY KEY,
  product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  store_id BIGINT NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  promo_price DECIMAL(10,2) NOT NULL,
  promo_label TEXT,
  valid_from DATE NOT NULL,
  valid_until DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (store_id, product_id)
);

-- Current week promotions (29.05 - 04.06.2026)
DO $$
DECLARE
  v_from DATE := '2026-05-29';
  v_until DATE := '2026-06-04';
BEGIN

  -- LIDL
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 7.99, '-55%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%szynka%' AND s.name = 'Lidl' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 3.49, '-30%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%mleko%' AND s.name = 'Lidl' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 19.99, '-20%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%pierś z kurczaka%' AND s.name = 'Lidl' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  -- BIEDRONKA
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 7.99, 'oferta tyg.', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%jajka%' AND s.name = 'Biedronka' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 5.99, '-20%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%masło%' AND p.name NOT ILIKE '%orzechowe%' AND s.name = 'Biedronka' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 3.49, '-30%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%chipsy%' AND s.name = 'Biedronka' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  -- KAUFLAND
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 22.99, '-15%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%pierś z kurczaka%' AND s.name = 'Kaufland' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 6.99, '-25%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%ser żółty%' AND s.name = 'Kaufland' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  -- ALDI
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 2.99, '-25%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%jogurt naturalny%' AND s.name = 'Aldi' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

END $$;

-- Verify: show inserted promos
SELECT pr.promo_price, pr.promo_label, pr.valid_from, pr.valid_until,
       p.name AS product, s.name AS store
FROM promotions pr
JOIN products p ON p.id = pr.product_id
JOIN stores s ON s.id = pr.store_id
ORDER BY s.name, p.name;
