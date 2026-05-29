-- Current week promotions (week 29.05 - 04.06.2026)
-- Add/update these every week from store leaflets

DO $$
DECLARE
  v_from DATE := '2026-05-29';
  v_until DATE := '2026-06-04';
BEGIN

  -- LIDL promotions
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

  -- BIEDRONKA promotions
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 7.99, 'oferta tygodnia', v_from, v_until
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
  WHERE p.name ILIKE '%chipsy%' AND p.name NOT ILIKE '%lay%' AND s.name = 'Biedronka' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

  -- KAUFLAND promotions
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

  -- ALDI promotions
  INSERT INTO promotions (product_id, store_id, promo_price, promo_label, valid_from, valid_until)
  SELECT p.id, s.id, 2.99, '-25%', v_from, v_until
  FROM products p, stores s
  WHERE p.name ILIKE '%jogurt naturalny%' AND s.name = 'Aldi' LIMIT 1
  ON CONFLICT (store_id, product_id) DO UPDATE SET
    promo_price = EXCLUDED.promo_price, promo_label = EXCLUDED.promo_label,
    valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until;

END $$;
