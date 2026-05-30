-- Adds loose/weight-sold products commonly seen on Polish receipts
-- (ids 543+). Run ONCE in Supabase SQL Editor.
--
-- NOTE: 13 names that were duplicates of earlier seeds (Cukinia,
-- Bakłażan, Burak, Por, Gruszki, Śliwki, Brzoskwinie, Nektarynki,
-- Grejpfrut, Imbir, Tofu, Komosa ryżowa, Filet z dorsza) have been
-- removed from this file. They already exist with lower ids.

INSERT INTO products (id, name, unit) VALUES
  (543, 'Patyczki do szaszłyków', '100 szt.'),
  (545, 'Filet z mintaja',        '1kg'),
  (546, 'Pstrąg',                 '1kg'),
  (547, 'Karp',                   '1kg'),
  (548, 'Makrela',                '1kg'),
  (551, 'Cukinia żółta',          '1kg'),
  (552, 'Dynia',                  '1kg'),
  (554, 'Seler',                  '1kg'),
  (555, 'Pietruszka korzeń',      '1kg'),
  (556, 'Pietruszka natka',       '1 pęczek'),
  (557, 'Koperek',                '1 pęczek'),
  (558, 'Szczypior',               '1 pęczek'),
  (560, 'Rzodkiewka',             '1 pęczek'),
  (561, 'Kapusta pekińska',       '1 szt.'),
  (562, 'Kapusta czerwona',       '1kg'),
  (563, 'Kalafior',               '1 szt.'),
  (564, 'Brukselka',              '500g'),
  (569, 'Czereśnie',              '1kg'),
  (570, 'Mandarynki',             '1kg'),
  (572, 'Ananas',                 '1 szt.'),
  (573, 'Granat',                 '1 szt.'),
  (575, 'Limonka',                '1 szt.'),
  (576, 'Karkówka',               '1kg'),
  (577, 'Żeberka',                '1kg'),
  (578, 'Schab bez kości',        '1kg'),
  (579, 'Łopatka',                '1kg'),
  (580, 'Mielone wieprzowe',      '500g'),
  (581, 'Filet z kurczaka',       '1kg'),
  (582, 'Wątróbka drobiowa',      '400g'),
  (583, 'Krewetki mrożone',       '200g'),
  (585, 'Kasza pęczak',           '500g'),
  (586, 'Kasza manna',            '400g'),
  (588, 'Bułki kajzerki',         '6 szt.'),
  (589, 'Chleb żytni',            '500g'),
  (590, 'Chleb pełnoziarnisty',   '500g')
ON CONFLICT DO NOTHING;

-- Base prices (Biedronka reference, PLN).
WITH base_prices(product_id, base) AS (
  VALUES
    (543, 6.99::numeric), (545, 35.99), (546, 39.99),
    (547, 22.99), (548, 26.99),
    (551, 12.99), (552, 5.99),       (554, 7.99),
    (555, 9.99),  (556, 2.99), (557, 2.49), (558, 2.99),
                  (560, 2.99), (561, 4.99), (562, 4.49),
    (563, 6.99),  (564, 7.99),
    (569, 24.99), (570, 8.99),
                  (572, 9.99), (573, 7.99),
    (575, 1.49),  (576, 25.99), (577, 22.99), (578, 19.99),
    (579, 18.99), (580, 14.99), (581, 21.99), (582, 9.99),
    (583, 13.99),
    (585, 4.49),  (586, 3.99),
                  (588, 3.99), (589, 5.49), (590, 5.99)
),
store_factors(store_name, factor) AS (
  VALUES
    ('Biedronka', 1.00::numeric),
    ('Lidl',      0.97),
    ('Aldi',      0.98),
    ('Kaufland',  1.05),
    ('Netto',     0.99),
    ('Auchan',    1.06),
    ('Carrefour', 1.08)
)
INSERT INTO prices (product_id, store_id, price, source, scraped_at)
SELECT
  bp.product_id,
  s.id,
  ROUND((bp.base * sf.factor)::numeric, 2) AS price,
  'estimated' AS source,
  NULL AS scraped_at
FROM base_prices bp
CROSS JOIN store_factors sf
JOIN stores s ON s.name = sf.store_name
ON CONFLICT (product_id, store_id) DO NOTHING;

-- Verification
SELECT COUNT(*) AS new_products    FROM products WHERE id BETWEEN 543 AND 590;
SELECT COUNT(*) AS new_price_rows  FROM prices   WHERE product_id BETWEEN 543 AND 590;
