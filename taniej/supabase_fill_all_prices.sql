-- Fill ALL products missing a Biedronka price with category-based estimates
-- Then propagate to all 7 stores via ratios
-- Safe: ON CONFLICT DO NOTHING won't overwrite real prices

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

  -- Step 1: fill Biedronka price for every product that lacks one
  -- Uses category heuristics from product name
  INSERT INTO prices (product_id, store_id, price)
  SELECT p.id, bid,
    CASE
      -- Meat / fish
      WHEN p.name ILIKE '%filet%' OR p.name ILIKE '%łosoś%' OR p.name ILIKE '%dorsz%' THEN 24.99
      WHEN p.name ILIKE '%indyk%' OR p.name ILIKE '%kurczak%' OR p.name ILIKE '%pierś%' THEN 22.99
      WHEN p.name ILIKE '%mielone%' OR p.name ILIKE '%wołowina%' THEN 19.99
      WHEN p.name ILIKE '%kiełbasa%' OR p.name ILIKE '%parówki%' OR p.name ILIKE '%kabanos%' THEN 9.99
      WHEN p.name ILIKE '%szynka%' OR p.name ILIKE '%salami%' OR p.name ILIKE '%mortadela%' THEN 9.99
      WHEN p.name ILIKE '%boczek%' OR p.name ILIKE '%bekon%' THEN 12.99
      WHEN p.name ILIKE '%tuńczyk%' OR p.name ILIKE '%sardynki%' OR p.name ILIKE '%makrela%' THEN 5.49
      -- Dairy
      WHEN p.name ILIKE '%śmietana%' OR p.name ILIKE '%śmietanka%' THEN 2.99
      WHEN p.name ILIKE '%jogurt%' OR p.name ILIKE '%kefir%' THEN 2.99
      WHEN p.name ILIKE '%twaróg%' OR p.name ILIKE '%ricotta%' OR p.name ILIKE '%cottage%' THEN 5.99
      WHEN p.name ILIKE '%ser biały%' OR p.name ILIKE '%ser twarogowy%' THEN 6.49
      WHEN p.name ILIKE '%ser żółty%' OR p.name ILIKE '%gouda%' OR p.name ILIKE '%edam%' THEN 8.99
      WHEN p.name ILIKE '%ser%' OR p.name ILIKE '%mozzarella%' OR p.name ILIKE '%feta%' THEN 7.99
      WHEN p.name ILIKE '%masło%' AND p.name NOT ILIKE '%orzechowe%' THEN 7.49
      WHEN p.name ILIKE '%mleko%' THEN 3.99
      WHEN p.name ILIKE '%śmietana%' THEN 2.99
      -- Bread / bakery
      WHEN p.name ILIKE '%chleb%' OR p.name ILIKE '%bułki%' OR p.name ILIKE '%bagietka%' THEN 4.49
      WHEN p.name ILIKE '%bułka%' THEN 1.29
      WHEN p.name ILIKE '%croissant%' THEN 2.99
      -- Eggs
      WHEN p.name ILIKE '%jajka%' OR p.name ILIKE '%jaja%' THEN 8.99
      -- Drinks
      WHEN p.name ILIKE '%red bull%' OR p.name ILIKE '%monster%' OR p.name ILIKE '%burn%' THEN 6.49
      WHEN p.name ILIKE '%sok%' AND p.name NOT ILIKE '%sokowirówka%' THEN 4.99
      WHEN p.name ILIKE '%cola%' OR p.name ILIKE '%fanta%' OR p.name ILIKE '%sprite%' THEN 3.49
      WHEN p.name ILIKE '%pepsi%' OR p.name ILIKE '%mountain dew%' THEN 3.49
      WHEN p.name ILIKE '%piwo%' OR p.name ILIKE '%beer%' THEN 3.49
      WHEN p.name ILIKE '%wino%' OR p.name ILIKE '%wine%' THEN 19.99
      WHEN p.name ILIKE '%wódka%' OR p.name ILIKE '%whisky%' OR p.name ILIKE '%rum%' THEN 49.99
      WHEN p.name ILIKE '%herbata%' OR p.name ILIKE '%tea%' THEN 7.99
      WHEN p.name ILIKE '%kawa%' OR p.name ILIKE '%coffee%' THEN 14.99
      WHEN p.name ILIKE '%kakao%' OR p.name ILIKE '%cocoa%' THEN 6.99
      WHEN p.name ILIKE '%woda%' AND p.name ILIKE '%gazow%' THEN 1.99
      WHEN p.name ILIKE '%woda%' THEN 1.99
      WHEN p.name ILIKE '%żywiec zdrój%' OR p.name ILIKE '%cisowianka%' OR p.name ILIKE '%żywiec%' THEN 2.29
      -- Snacks / sweets
      WHEN p.name ILIKE '%pringles%' THEN 7.99
      WHEN p.name ILIKE '%lay%' OR p.name ILIKE '%lays%' THEN 5.49
      WHEN p.name ILIKE '%chipsy%' THEN 5.49
      WHEN p.name ILIKE '%snickers%' OR p.name ILIKE '%twix%' OR p.name ILIKE '%mars%' OR p.name ILIKE '%bounty%' THEN 2.99
      WHEN p.name ILIKE '%milka%' OR p.name ILIKE '%toblerone%' THEN 4.49
      WHEN p.name ILIKE '%czekolada%' THEN 3.49
      WHEN p.name ILIKE '%nutella%' OR p.name ILIKE '%krem czekoladowy%' THEN 12.99
      WHEN p.name ILIKE '%ferrero%' OR p.name ILIKE '%raffaello%' THEN 6.99
      WHEN p.name ILIKE '%oreo%' OR p.name ILIKE '%prince%' THEN 5.99
      WHEN p.name ILIKE '%wafel%' OR p.name ILIKE '%wafle%' THEN 3.99
      WHEN p.name ILIKE '%biszkopty%' OR p.name ILIKE '%herbatniki%' THEN 4.49
      WHEN p.name ILIKE '%cukierki%' OR p.name ILIKE '%landrynki%' THEN 3.99
      WHEN p.name ILIKE '%żelki%' OR p.name ILIKE '%gummy%' THEN 3.99
      WHEN p.name ILIKE '%lody%' OR p.name ILIKE '%ice cream%' THEN 5.99
      WHEN p.name ILIKE '%miód%' THEN 12.99
      WHEN p.name ILIKE '%dżem%' OR p.name ILIKE '%marmolada%' THEN 6.49
      WHEN p.name ILIKE '%musli%' OR p.name ILIKE '%granola%' THEN 6.49
      WHEN p.name ILIKE '%płatki%' THEN 3.99
      -- Pantry staples
      WHEN p.name ILIKE '%mąka%' THEN 3.49
      WHEN p.name ILIKE '%ryż%' THEN 4.49
      WHEN p.name ILIKE '%makaron%' OR p.name ILIKE '%spaghetti%' OR p.name ILIKE '%penne%' THEN 2.99
      WHEN p.name ILIKE '%kasza%' OR p.name ILIKE '%quinoa%' THEN 3.99
      WHEN p.name ILIKE '%cukier%' THEN 3.49
      WHEN p.name ILIKE '%sól%' THEN 1.79
      WHEN p.name ILIKE '%pieprz%' OR p.name ILIKE '%papryka miel%' THEN 3.49
      WHEN p.name ILIKE '%przypraw%' OR p.name ILIKE '%zioła%' THEN 3.99
      WHEN p.name ILIKE '%olej%' OR p.name ILIKE '%oleiwa%' THEN 5.99
      WHEN p.name ILIKE '%oliwa%' THEN 14.99
      WHEN p.name ILIKE '%ocet%' THEN 2.99
      WHEN p.name ILIKE '%ketchup%' THEN 5.99
      WHEN p.name ILIKE '%musztarda%' THEN 3.49
      WHEN p.name ILIKE '%majonez%' THEN 5.99
      WHEN p.name ILIKE '%sos%' THEN 4.99
      WHEN p.name ILIKE '%koncentrat%' THEN 3.49
      WHEN p.name ILIKE '%puszka%' OR p.name ILIKE '%konserwa%' THEN 4.99
      -- Vegetables / fruit
      WHEN p.name ILIKE '%banan%' OR p.name ILIKE '%jabłko%' OR p.name ILIKE '%gruszka%' THEN 3.99
      WHEN p.name ILIKE '%pomidor%' OR p.name ILIKE '%ogórek%' THEN 5.99
      WHEN p.name ILIKE '%marchew%' OR p.name ILIKE '%ziemniak%' OR p.name ILIKE '%cebula%' THEN 2.99
      WHEN p.name ILIKE '%sałata%' OR p.name ILIKE '%szpinak%' OR p.name ILIKE '%rukola%' THEN 3.49
      WHEN p.name ILIKE '%brokuł%' OR p.name ILIKE '%kalafior%' OR p.name ILIKE '%kapusta%' THEN 3.99
      WHEN p.name ILIKE '%papryka%' AND p.name NOT ILIKE '%miel%' THEN 4.99
      WHEN p.name ILIKE '%czosnek%' THEN 2.49
      WHEN p.name ILIKE '%owoc%' OR p.name ILIKE '%truskawka%' OR p.name ILIKE '%malina%' THEN 9.99
      -- Frozen
      WHEN p.name ILIKE '%mrożone%' OR p.name ILIKE '%zamrożone%' THEN 7.99
      WHEN p.name ILIKE '%pizza%' THEN 9.99
      -- Hygiene / household
      WHEN p.name ILIKE '%szampon%' OR p.name ILIKE '%odżywka%' THEN 12.99
      WHEN p.name ILIKE '%pasta do zębów%' OR p.name ILIKE '%toothpaste%' THEN 5.99
      WHEN p.name ILIKE '%mydło%' OR p.name ILIKE '%żel pod prysznic%' THEN 7.99
      WHEN p.name ILIKE '%dezodorant%' OR p.name ILIKE '%antyperspirant%' THEN 9.99
      WHEN p.name ILIKE '%papier toaletowy%' OR p.name ILIKE '%chusteczki%' THEN 14.99
      WHEN p.name ILIKE '%ręcznik papierowy%' THEN 9.99
      WHEN p.name ILIKE '%płyn do naczyń%' OR p.name ILIKE '%płyn do mycia%' THEN 5.99
      WHEN p.name ILIKE '%proszek%' OR p.name ILIKE '%kapsułki do prania%' THEN 24.99
      WHEN p.name ILIKE '%płyn do płukania%' OR p.name ILIKE '%fabric softener%' THEN 14.99
      WHEN p.name ILIKE '%zmywak%' OR p.name ILIKE '%gąbka%' THEN 2.99
      -- Bread spreads / sauces
      WHEN p.name ILIKE '%masło orzechowe%' OR p.name ILIKE '%peanut%' THEN 9.99
      WHEN p.name ILIKE '%tahini%' OR p.name ILIKE '%hummus%' THEN 8.99
      -- Default by broad category
      ELSE 5.99
    END
  FROM products p
  WHERE NOT EXISTS (
    SELECT 1 FROM prices WHERE product_id = p.id AND store_id = bid
  );

  -- Step 2: propagate to all other stores using ratios
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

-- How many products now have full coverage?
SELECT
  COUNT(DISTINCT product_id) AS products_with_prices,
  COUNT(*) AS total_price_entries,
  (SELECT COUNT(*) FROM products) AS total_products
FROM prices;
