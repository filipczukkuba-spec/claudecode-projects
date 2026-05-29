-- Fill every product still missing a Biedronka price using exact name lookup
-- Then propagate to all 7 stores
-- Run this ONCE — ON CONFLICT DO NOTHING skips already-filled entries

DO $$
DECLARE
  bid INT; lid INT; kauf INT; aldi_id INT; netto INT; auch INT; carr INT;
  pid INT;
  rec RECORD;
BEGIN
  SELECT id INTO bid     FROM stores WHERE name = 'Biedronka';
  SELECT id INTO lid     FROM stores WHERE name = 'Lidl';
  SELECT id INTO kauf    FROM stores WHERE name = 'Kaufland';
  SELECT id INTO aldi_id FROM stores WHERE name = 'Aldi';
  SELECT id INTO netto   FROM stores WHERE name = 'Netto';
  SELECT id INTO auch    FROM stores WHERE name = 'Auchan';
  SELECT id INTO carr    FROM stores WHERE name = 'Carrefour';

  -- Direct name → Biedronka price mapping
  -- Using ILIKE so case differences don't matter
  FOR rec IN
    SELECT * FROM (VALUES
      -- Dairy & eggs
      ('Mleko',                3.99),
      ('Mleko UHT',            3.69),
      ('Jajka',                8.99),
      ('Masło',                7.49),
      ('Ser żółty',           38.99),
      ('Ser biały',            6.49),
      ('Jogurt naturalny',     2.99),
      ('Actimel',              2.99),
      ('Activia jogurt',       2.99),
      ('Danio serek',          2.99),
      ('Zott Monte',           2.99),
      ('Piątnica śmietana',    2.79),
      -- Meat
      ('Pierś z kurczaka',    24.99),
      ('Kabanosy',             7.99),
      -- Bread
      ('Chleb',                4.49),
      -- Drinks
      ('Coca-Cola',            3.49),
      ('Coca-Cola Zero',       3.49),
      ('Pepsi Max',            3.49),
      ('Woda mineralna',       1.99),
      ('Woda gazowana',        1.99),
      ('Żywiec Zdrój',         2.29),
      ('Cisowianka',           2.49),
      ('Red Bull',             6.49),
      ('Monster Energy',       6.49),
      ('Tiger Energy',         4.49),
      ('Hortex sok',           4.99),
      ('Tymbark sok',          3.99),
      -- Pantry
      ('Ryż',                  4.49),
      ('Makaron',              2.99),
      ('Cukier',               3.49),
      ('Sól',                  1.79),
      ('Ketchup',              5.99),
      ('Majonez',              5.99),
      ('Musztarda',            3.49),
      ('Olej słonecznikowy',   5.99),
      ('Marchew',              2.99),
      ('Pomidory',             5.99),
      ('Jabłka',               3.99),
      ('Banany',               3.99),
      ('Płatki owsiane',       3.99),
      ('Piwo',                 3.49),
      ('Papier toaletowy',    14.99),
      ('Szampon',             12.99),
      ('Pasta do zębów',       5.99),
      -- Snacks & candy
      ('Snickers',             2.99),
      ('Twix',                 2.99),
      ('Mars',                 2.99),
      ('Bounty',               2.99),
      ('Milky Way',            2.49),
      ('Lion',                 2.49),
      ('Kit Kat',              2.99),
      ('Kinder Bueno',         3.99),
      ('Kinder czekolada',     3.99),
      ('Prince Polo',          1.49),
      ('After Eight',          7.99),
      ('Toblerone',            7.99),
      ('Raffaello',            6.99),
      ('Ferrero Rocher',       6.99),
      ('Milka Mleczna',        3.99),
      ('Milka Oreo',           4.49),
      ('Milka Karmel',         4.49),
      ('Milka Strawberry',     4.49),
      ('Milka White',          4.49),
      ('Wawel Czekolada Mleczna', 3.49),
      ('Wedel Czekolada',      3.49),
      ('Czekolada biała',      3.99),
      ('Czekolada deserowa 70%', 4.99),
      ('Czekolada gorzka',     3.99),
      ('Czekolada mleczna',    3.49),
      ('Czekolada karmelowa',  3.99),
      ('Czekolada z kokosem',  3.99),
      ('Czekolada z migdałami', 4.49),
      ('Czekolada z orzechami', 4.49),
      ('Czekolada z rodzynkami', 3.99),
      ('Czekolada z truskawkami', 3.99),
      ('Czekolada bez cukru',  4.49),
      ('Daktyle w czekoladzie', 6.99),
      ('Chałwa',               5.49),
      ('Nugat',                4.99),
      ('Oreo',                 5.99),
      ('Oreo Double Stuf',     6.49),
      ('Lotus Biscoff',        9.99),
      ('Digestive McVitie\'s', 7.99),
      ('Leibniz',              7.49),
      ('BelVita',              6.99),
      ('Herbatniki',           4.49),
      ('Delicje',              5.99),
      ('Ciastka',              5.49),
      ('Ciastka kakaowe',      4.99),
      ('Ciastka kokosowe',     4.99),
      ('Ciastka maślane',      4.99),
      ('Ciastka owsiane',      4.99),
      ('Ciastka z dżemem',     4.99),
      ('Ciastka z kremem',     4.99),
      ('Ciastka z owocami',    4.99),
      ('Ciastka zbożowe',      4.99),
      ('Brownie',              2.99),
      ('Muffin czekoladowy',   2.99),
      ('Wafle czekoladowe',    4.99),
      ('Wafle ryżowe solone',  4.49),
      ('Wafle z kremem',       4.99),
      -- Chips & snacks
      ('Pringles Original',    7.99),
      ('Pringles Paprika',     7.99),
      ('Pringles BBQ',         7.99),
      ('Pringles Sour Cream',  7.99),
      ('Lay''s Papryka',       5.49),
      ('Lay''s Solone',        5.49),
      ('Lay''s Ser i Cebula',  5.49),
      ('Lay''s Max Papryka',   5.99),
      ('Lay''s Zesty BBQ',     5.49),
      ('Chipsy batatowe',      5.49),
      ('Chipsy cebulowe',      4.99),
      ('Chipsy o smaku szynki', 4.99),
      ('Chipsy paprykowe',     4.99),
      ('Chipsy pełnoziarniste', 5.49),
      ('Chipsy pikantne',      4.99),
      ('Chipsy pita',          5.99),
      ('Chipsy serowe',        4.99),
      ('Chipsy solone',        4.99),
      ('Chipsy tortilla',      5.99),
      ('Chipsy warzywne',      5.49),
      ('Precelki solone',      3.99),
      ('Popcorn karmelowy',    3.49),
      ('Popcorn maślany',      3.49),
      ('Popcorn serowy',       3.49),
      ('Popcorn słony',        3.49),
      ('Chrupki ryżowe',       3.99),
      ('Chrupki zbożowe',      3.99),
      ('Grissini',             3.99),
      ('Krakersy pełnoziarniste', 4.49),
      ('Krakersy ryżowe',      3.99),
      ('Krakersy z ziarnami',  4.49),
      ('Paluszki z sezamem',   3.99),
      ('Paluszki mięsne',      6.99),
      ('Musli',                6.49),
      ('Granola',              6.99),
      ('Mix bakaliów',         7.99),
      ('Orzechy laskowe',      9.99),
      ('Orzechy makadamia',   14.99),
      ('Orzeszki miodowe',     6.99),
      ('Orzeszki w czekoladzie', 7.99),
      ('Orzeszki ziemne',      4.99),
      ('Słonecznik prażony',   3.99),
      ('Dynia prażona',        4.99),
      ('Suszone banany',       4.99),
      ('Suszone figi',         6.99),
      ('Suszone jabłka',       5.99),
      ('Suszone mango',        6.99),
      ('Suszone morele',       6.99),
      ('Suszone śliwki',       6.49),
      ('Suszone mięso wołowe', 12.99),
      ('Biltong',             12.99),
      -- Ice cream
      ('Ben & Jerry''s',      14.99),
      ('Cornetto',             4.49),
      ('Magnum Classic',       5.49),
      ('Magnum Almond',        5.49),
      ('Lody Magnum style',    5.49),
      ('Koral lody',           6.99),
      ('Lody czekoladowe',     6.99),
      ('Lody truskawkowe',     6.99),
      ('Lody waniliowe',       6.99),
      ('Lody rożek',           3.49),
      ('Sorbet owocowy',       6.99),
      -- Drinks more
      ('Alpro sojowe',         7.49),
      ('Oatly owsiane',        7.49),
      -- Candy
      ('Cukierki krówki',      3.99),
      ('Cukierki miętowe',     2.99),
      ('Cukierki owocowe',     2.99),
      ('Karmelki krówkowe',    3.99),
      ('Landrynki',            2.99),
      ('Dropsy miętowe',       2.99),
      ('Lizaki',               2.99),
      ('Pianka cukrowa',       2.99),
      ('Żelki',                3.49),
      ('Żelki cola',           3.49),
      ('Żelki kwaśne',         3.49),
      ('Żelki misie',          3.49),
      ('Żelki witaminowe',     4.99),
      ('Guma do żucia',        2.49),
      -- Sauces & condiments
      ('Heinz ketchup',        8.99),
      ('Kielecki majonez',     7.99),
      ('Hellmann''s majonez',  7.99),
      ('Winiary majonez',      5.99),
      ('Skippy Peanut Butter', 14.99),
      -- Soups
      ('Knorr zupa',           2.49),
      ('Maggi zupa',           2.49),
      ('Winiary zupa',         2.49),
      -- Dairy drink
      ('Actimel',              2.99),
      -- Frozen
      ('Pierogi mrożone',      9.99),
      -- Hygiene
      ('Proszek do zmywarki',  19.99),
      -- Vegetables & fruit
      ('Ziemniaki',            2.99),
      ('Jabłka',               3.99),
      ('Marchew',              2.99),
      ('Pomidory',             5.99)
    ) AS t(pname, bprice)
  LOOP
    SELECT id INTO pid FROM products WHERE name ILIKE rec.pname LIMIT 1;
    IF pid IS NOT NULL THEN
      INSERT INTO prices (product_id, store_id, price)
      VALUES (pid, bid, rec.bprice)
      ON CONFLICT (product_id, store_id) DO NOTHING;
    END IF;
  END LOOP;

  -- Fallback: anything STILL missing a Biedronka price gets 4.99
  INSERT INTO prices (product_id, store_id, price)
  SELECT p.id, bid, 4.99
  FROM products p
  WHERE NOT EXISTS (SELECT 1 FROM prices WHERE product_id = p.id AND store_id = bid)
  ON CONFLICT (product_id, store_id) DO NOTHING;

  -- Propagate ALL missing store prices from Biedronka base
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

-- Check coverage
SELECT
  (SELECT COUNT(*) FROM products) AS total_products,
  COUNT(DISTINCT product_id) AS products_with_biedronka_price,
  COUNT(*) AS total_price_entries
FROM prices
WHERE store_id = (SELECT id FROM stores WHERE name = 'Biedronka');
