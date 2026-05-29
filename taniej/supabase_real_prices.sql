-- Real price update for 25 key products across all 7 stores
-- Based on approximate market prices (May 2026)
-- VERIFY a few prices on store websites before running!

DO $$
DECLARE
  v_product_id INT;
  v_store RECORD;
  v_prices JSONB;
BEGIN

  -- Helper: update price for one product across all stores
  -- Format: {"Biedronka": price, "Lidl": price, ...}

  -- 1. Mleko
  SELECT id INTO v_product_id FROM products WHERE name = 'Mleko' LIMIT 1;
  v_prices := '{"Biedronka":2.89,"Lidl":2.79,"Kaufland":2.99,"Aldi":2.69,"Netto":2.99,"Auchan":2.89,"Carrefour":3.19}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 2. Chleb
  SELECT id INTO v_product_id FROM products WHERE name = 'Chleb' LIMIT 1;
  v_prices := '{"Biedronka":3.49,"Lidl":3.29,"Kaufland":3.99,"Aldi":3.29,"Netto":3.79,"Auchan":3.89,"Carrefour":4.29}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 3. Jajka
  SELECT id INTO v_product_id FROM products WHERE name = 'Jajka' LIMIT 1;
  v_prices := '{"Biedronka":8.99,"Lidl":8.49,"Kaufland":9.49,"Aldi":7.99,"Netto":8.99,"Auchan":9.29,"Carrefour":9.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 4. Masło
  SELECT id INTO v_product_id FROM products WHERE name = 'Masło' LIMIT 1;
  v_prices := '{"Biedronka":6.49,"Lidl":5.99,"Kaufland":6.99,"Aldi":5.99,"Netto":6.79,"Auchan":6.99,"Carrefour":7.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 5. Ser żółty
  SELECT id INTO v_product_id FROM products WHERE name = 'Ser żółty' LIMIT 1;
  v_prices := '{"Biedronka":22.99,"Lidl":21.99,"Kaufland":24.99,"Aldi":20.99,"Netto":23.49,"Auchan":25.99,"Carrefour":27.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 6. Jogurt naturalny
  SELECT id INTO v_product_id FROM products WHERE name = 'Jogurt naturalny' LIMIT 1;
  v_prices := '{"Biedronka":2.99,"Lidl":2.79,"Kaufland":3.29,"Aldi":2.69,"Netto":3.09,"Auchan":3.29,"Carrefour":3.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 7. Ryż
  SELECT id INTO v_product_id FROM products WHERE name = 'Ryż' LIMIT 1;
  v_prices := '{"Biedronka":4.49,"Lidl":3.99,"Kaufland":4.99,"Aldi":3.89,"Netto":4.49,"Auchan":4.99,"Carrefour":5.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 8. Makaron
  SELECT id INTO v_product_id FROM products WHERE name = 'Makaron' LIMIT 1;
  v_prices := '{"Biedronka":2.99,"Lidl":2.79,"Kaufland":3.49,"Aldi":2.79,"Netto":3.29,"Auchan":3.49,"Carrefour":3.79}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 9. Cukier
  SELECT id INTO v_product_id FROM products WHERE name = 'Cukier' LIMIT 1;
  v_prices := '{"Biedronka":3.29,"Lidl":3.19,"Kaufland":3.49,"Aldi":2.99,"Netto":3.39,"Auchan":3.49,"Carrefour":3.79}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 10. Sól
  SELECT id INTO v_product_id FROM products WHERE name ILIKE 'Sól' LIMIT 1;
  v_prices := '{"Biedronka":1.99,"Lidl":1.89,"Kaufland":2.29,"Aldi":1.89,"Netto":2.19,"Auchan":2.29,"Carrefour":2.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL AND v_product_id IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 11. Olej słonecznikowy
  SELECT id INTO v_product_id FROM products WHERE name = 'Olej słonecznikowy' LIMIT 1;
  v_prices := '{"Biedronka":6.99,"Lidl":6.49,"Kaufland":7.49,"Aldi":6.29,"Netto":7.29,"Auchan":7.49,"Carrefour":7.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 12. Ketchup
  SELECT id INTO v_product_id FROM products WHERE name = 'Ketchup' LIMIT 1;
  v_prices := '{"Biedronka":4.99,"Lidl":4.49,"Kaufland":5.49,"Aldi":4.29,"Netto":5.29,"Auchan":5.49,"Carrefour":5.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 13. Majonez
  SELECT id INTO v_product_id FROM products WHERE name = 'Majonez' LIMIT 1;
  v_prices := '{"Biedronka":6.49,"Lidl":5.99,"Kaufland":6.99,"Aldi":5.79,"Netto":6.79,"Auchan":6.99,"Carrefour":7.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 14. Pomidory
  SELECT id INTO v_product_id FROM products WHERE name = 'Pomidory' LIMIT 1;
  v_prices := '{"Biedronka":6.99,"Lidl":6.49,"Kaufland":7.49,"Aldi":6.29,"Netto":7.29,"Auchan":7.99,"Carrefour":8.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 15. Ziemniaki
  SELECT id INTO v_product_id FROM products WHERE name = 'Ziemniaki' LIMIT 1;
  v_prices := '{"Biedronka":2.99,"Lidl":2.79,"Kaufland":3.29,"Aldi":2.69,"Netto":3.19,"Auchan":3.29,"Carrefour":3.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 16. Marchew
  SELECT id INTO v_product_id FROM products WHERE name = 'Marchew' LIMIT 1;
  v_prices := '{"Biedronka":2.49,"Lidl":2.29,"Kaufland":2.79,"Aldi":2.19,"Netto":2.69,"Auchan":2.79,"Carrefour":2.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 17. Jabłka
  SELECT id INTO v_product_id FROM products WHERE name = 'Jabłka' LIMIT 1;
  v_prices := '{"Biedronka":4.49,"Lidl":3.99,"Kaufland":4.99,"Aldi":3.89,"Netto":4.49,"Auchan":4.99,"Carrefour":5.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 18. Banany
  SELECT id INTO v_product_id FROM products WHERE name = 'Banany' LIMIT 1;
  v_prices := '{"Biedronka":3.99,"Lidl":3.79,"Kaufland":4.49,"Aldi":3.69,"Netto":4.29,"Auchan":4.49,"Carrefour":4.79}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 19. Pierś z kurczaka
  SELECT id INTO v_product_id FROM products WHERE name = 'Pierś z kurczaka' LIMIT 1;
  v_prices := '{"Biedronka":16.99,"Lidl":15.99,"Kaufland":18.99,"Aldi":15.49,"Netto":17.99,"Auchan":18.99,"Carrefour":19.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 20. Coca-Cola
  SELECT id INTO v_product_id FROM products WHERE name = 'Coca-Cola' LIMIT 1;
  v_prices := '{"Biedronka":3.99,"Lidl":3.79,"Kaufland":4.29,"Aldi":3.69,"Netto":3.99,"Auchan":4.49,"Carrefour":4.49}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 21. Woda mineralna
  SELECT id INTO v_product_id FROM products WHERE name = 'Woda mineralna' LIMIT 1;
  v_prices := '{"Biedronka":1.79,"Lidl":1.69,"Kaufland":1.99,"Aldi":1.59,"Netto":1.89,"Auchan":1.99,"Carrefour":2.19}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 22. Płatki owsiane
  SELECT id INTO v_product_id FROM products WHERE name = 'Płatki owsiane' LIMIT 1;
  v_prices := '{"Biedronka":3.49,"Lidl":3.29,"Kaufland":3.79,"Aldi":2.99,"Netto":3.69,"Auchan":3.79,"Carrefour":3.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 23. Lay's Papryka
  SELECT id INTO v_product_id FROM products WHERE name ILIKE '%Lay%Papryka%' LIMIT 1;
  v_prices := '{"Biedronka":5.99,"Lidl":5.49,"Kaufland":6.49,"Aldi":5.29,"Netto":5.99,"Auchan":6.49,"Carrefour":6.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL AND v_product_id IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 24. Ser biały
  SELECT id INTO v_product_id FROM products WHERE name = 'Ser biały' LIMIT 1;
  v_prices := '{"Biedronka":3.49,"Lidl":3.29,"Kaufland":3.79,"Aldi":3.29,"Netto":3.69,"Auchan":3.79,"Carrefour":3.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

  -- 25. Papier toaletowy
  SELECT id INTO v_product_id FROM products WHERE name = 'Papier toaletowy' LIMIT 1;
  v_prices := '{"Biedronka":8.99,"Lidl":8.49,"Kaufland":9.99,"Aldi":8.29,"Netto":9.49,"Auchan":9.99,"Carrefour":10.99}';
  FOR v_store IN SELECT id, name FROM stores LOOP
    IF (v_prices->>v_store.name) IS NOT NULL THEN
      UPDATE prices SET price = (v_prices->>v_store.name)::NUMERIC
      WHERE product_id = v_product_id AND store_id = v_store.id;
    END IF;
  END LOOP;

END $$;
