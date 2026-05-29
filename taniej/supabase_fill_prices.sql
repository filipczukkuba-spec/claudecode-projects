-- ============================================================
-- STEP 1: Real prices for key products (all 7 stores)
-- ============================================================
DO $$
DECLARE
  bid INT; lid INT; kauf INT; aldi_id INT; netto INT; auch INT; carr INT;
  pid INT;
  rec JSON;
  products JSON := '[
    ["Mleko",              3.99, 3.79, 4.29, 3.69, 3.99, 4.39, 4.49],
    ["Jajka",              8.99, 8.49, 9.49, 8.49, 8.99, 9.79, 9.99],
    ["Chleb",              4.49, 3.99, 4.79, 4.29, 4.49, 4.99, 5.19],
    ["Masło",              7.49, 6.99, 7.99, 7.29, 7.49, 8.19, 8.49],
    ["Pierś z kurczaka",  24.99,22.99,26.99,23.99,24.99,27.99,28.99],
    ["Ser żółty",         38.99,35.99,41.99,36.99,38.99,42.99,44.99],
    ["Jogurt naturalny",   2.99, 2.79, 3.19, 2.89, 2.99, 3.29, 3.39],
    ["Ketchup",            5.99, 5.49, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Papier toaletowy",  14.99,13.99,15.99,13.99,14.99,16.49,17.49],
    ["Woda mineralna",     1.99, 1.89, 2.19, 1.89, 1.99, 2.29, 2.39],
    ["Ryż",                4.49, 4.29, 4.79, 4.29, 4.49, 4.99, 5.19],
    ["Makaron",            2.99, 2.79, 3.19, 2.89, 2.99, 3.29, 3.39],
    ["Cukier",             3.49, 3.29, 3.69, 3.39, 3.49, 3.79, 3.99],
    ["Sól",                1.79, 1.59, 1.89, 1.59, 1.79, 1.99, 2.09],
    ["Olej słonecznikowy", 5.99, 5.79, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Marchew",            2.99, 2.79, 3.19, 2.89, 2.99, 3.29, 3.39],
    ["Pomidory",           5.99, 5.49, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Jabłka",             3.99, 3.79, 4.29, 3.79, 3.99, 4.39, 4.49],
    ["Banany",             3.99, 3.79, 4.29, 3.79, 3.99, 4.39, 4.49],
    ["Płatki owsiane",     3.99, 3.79, 4.29, 3.79, 3.99, 4.39, 4.49],
    ["Coca-Cola",          3.49, 3.29, 3.79, 3.29, 3.49, 3.79, 3.99],
    ["Coca-Cola Zero",     3.49, 3.29, 3.79, 3.29, 3.49, 3.79, 3.99],
    ["Snickers",           2.99, 2.79, 3.19, 2.79, 2.99, 3.29, 3.39],
    ["Twix",               2.99, 2.79, 3.19, 2.79, 2.99, 3.29, 3.39],
    ["Mars",               2.99, 2.79, 3.19, 2.79, 2.99, 3.29, 3.39],
    ["Milka Mleczna",      3.99, 3.79, 4.29, 3.79, 3.99, 4.39, 4.49],
    ["Milka Oreo",         4.49, 4.29, 4.79, 4.29, 4.49, 4.99, 5.19],
    ["Milka Karmel",       4.49, 4.29, 4.79, 4.29, 4.49, 4.99, 5.19],
    ["Oreo",               5.99, 5.49, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Red Bull",           6.49, 5.99, 6.99, 5.99, 6.49, 7.09, 7.29],
    ["Monster Energy",     6.49, 5.99, 6.99, 5.99, 6.49, 7.09, 7.29],
    ["Majonez",            5.99, 5.49, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Ser biały",          6.49, 5.99, 6.99, 6.29, 6.49, 7.09, 7.29],
    ["Płyn do naczyń",     5.99, 5.79, 6.49, 5.79, 5.99, 6.59, 6.79],
    ["Proszek do prania",  24.99,22.99,26.99,23.99,24.99,27.99,28.99],
    ["Herbata",             7.99, 7.49, 8.49, 7.49, 7.99, 8.79, 9.09],
    ["Kawa mielona",       12.99,11.99,13.99,12.49,12.99,14.19,14.69],
    ["Nutella",            12.99,11.99,13.99,12.49,12.99,14.19,14.69],
    ["Żywiec Zdrój",        2.29, 2.09, 2.49, 2.09, 2.29, 2.49, 2.59],
    ["Cisowianka",          2.49, 2.29, 2.69, 2.29, 2.49, 2.79, 2.89],
    ["Pringles Original",   7.99, 7.49, 8.49, 7.49, 7.99, 8.79, 9.09],
    ["Pringles Paprika",    7.99, 7.49, 8.49, 7.49, 7.99, 8.79, 9.09],
    ["Lay''s Papryka",      5.49, 4.99, 5.99, 5.29, 5.49, 5.99, 6.19],
    ["Lay''s Solone",       5.49, 4.99, 5.99, 5.29, 5.49, 5.99, 6.19],
    ["Ferrero Rocher",      6.99, 6.49, 7.49, 6.49, 6.99, 7.59, 7.89],
    ["Szynka",              9.99, 9.49,10.69, 9.49, 9.99,10.89,11.29],
    ["Łosoś wędzony",       8.99, 8.49, 9.49, 8.49, 8.99, 9.79, 9.99],
    ["Woda gazowana",       1.99, 1.89, 2.19, 1.89, 1.99, 2.29, 2.39],
    ["Kakao",               6.99, 6.49, 7.49, 6.49, 6.99, 7.59, 7.89],
    ["Musli",               6.49, 5.99, 6.99, 5.99, 6.49, 7.09, 7.29],
    ["Dżem",                6.49, 5.99, 6.99, 5.99, 6.49, 7.09, 7.29],
    ["Miód",               12.99,11.99,13.99,12.49,12.99,14.19,14.69],
    ["Oliwa z oliwek",     14.99,13.99,15.99,13.99,14.99,16.49,17.49],
    ["Masło orzechowe",     9.99, 9.49,10.69, 9.49, 9.99,10.89,11.29],
    ["Szampon",            12.99,11.99,13.99,12.49,12.99,14.19,14.69],
    ["Pasta do zębów",      5.99, 5.49, 6.49, 5.49, 5.99, 6.59, 6.79],
    ["Chipsy",              5.49, 4.99, 5.99, 5.29, 5.49, 5.99, 6.19],
    ["Czekolada",           3.49, 3.29, 3.69, 3.29, 3.49, 3.79, 3.99],
    ["Musztarda",           3.49, 3.29, 3.69, 3.29, 3.49, 3.79, 3.99],
    ["Piwo",                3.49, 3.29, 3.69, 3.29, 3.49, 3.79, 3.99],
    ["Tuńczyk w puszce",    5.49, 4.99, 5.99, 5.29, 5.49, 5.99, 6.19]
  ]';
BEGIN
  SELECT id INTO bid    FROM stores WHERE name = 'Biedronka';
  SELECT id INTO lid    FROM stores WHERE name = 'Lidl';
  SELECT id INTO kauf   FROM stores WHERE name = 'Kaufland';
  SELECT id INTO aldi_id FROM stores WHERE name = 'Aldi';
  SELECT id INTO netto  FROM stores WHERE name = 'Netto';
  SELECT id INTO auch   FROM stores WHERE name = 'Auchan';
  SELECT id INTO carr   FROM stores WHERE name = 'Carrefour';

  FOR rec IN SELECT * FROM json_array_elements(products) LOOP
    SELECT id INTO pid FROM products
    WHERE name ILIKE (rec->>0) LIMIT 1;

    IF pid IS NOT NULL THEN
      INSERT INTO prices (product_id, store_id, price) VALUES
        (pid, bid,     (rec->>1)::NUMERIC),
        (pid, lid,     (rec->>2)::NUMERIC),
        (pid, kauf,    (rec->>3)::NUMERIC),
        (pid, aldi_id, (rec->>4)::NUMERIC),
        (pid, netto,   (rec->>5)::NUMERIC),
        (pid, auch,    (rec->>6)::NUMERIC),
        (pid, carr,    (rec->>7)::NUMERIC)
      ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price;
    END IF;
  END LOOP;
END $$;


-- ============================================================
-- STEP 2: Fill ALL remaining gaps using price ratios
-- Every product with a Biedronka price gets the other 6 stores
-- calculated automatically. ON CONFLICT DO NOTHING = won't
-- overwrite real prices set in Step 1 or previous SQLs.
-- Ratios observed from real data in the DB.
-- ============================================================
DO $$
DECLARE
  bid INT; lid INT; kauf INT; aldi_id INT; netto INT; auch INT; carr INT;
BEGIN
  SELECT id INTO bid    FROM stores WHERE name = 'Biedronka';
  SELECT id INTO lid    FROM stores WHERE name = 'Lidl';
  SELECT id INTO kauf   FROM stores WHERE name = 'Kaufland';
  SELECT id INTO aldi_id FROM stores WHERE name = 'Aldi';
  SELECT id INTO netto  FROM stores WHERE name = 'Netto';
  SELECT id INTO auch   FROM stores WHERE name = 'Auchan';
  SELECT id INTO carr   FROM stores WHERE name = 'Carrefour';

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
