-- Adds more Polish brand products (ids 431+) with estimated prices
-- across all 7 stores. Run ONCE in Supabase SQL Editor.
--
-- Strategy: insert each product with a single base price (Biedronka
-- reference), then cross-join with stores using store-specific
-- multipliers derived from historical comparison data.
--
-- The 'estimated' source is set so the new UI badges work correctly.

-- 1. Insert products. ON CONFLICT keeps the script idempotent.
INSERT INTO products (id, name, unit) VALUES
  -- Polish dairy
  (431, 'Mlekovita ser',            '250g'),
  (432, 'Mlekovita masło',          '200g'),
  (433, 'Piątnica twaróg',          '250g'),
  -- 434 'Piątnica śmietana' removed (duplicate of earlier seed)
  (435, 'Hochland ser topiony',     '200g'),
  (436, 'Hochland Almette',         '150g'),
  (437, 'Bakoma jogurt',            '150g'),
  (438, 'Bakoma Mus',               '100g'),
  (439, 'Zott Jogobella',           '150g'),
  -- 440 'Zott Monte' removed (duplicate of earlier seed)
  (441, 'Müller jogurt',            '150g'),
  (442, 'Skyr Pilos',               '150g'),
  (443, 'Mleko UHT Łaciate 3,2%',   '1L'),
  (444, 'Mleko UHT Łaciate 2%',     '1L'),
  (445, 'Mleko Wypasione',          '1L'),
  -- Polish meat
  (446, 'Sokołów szynka',           '300g'),
  (447, 'Sokołów kiełbasa',         '1kg'),
  (448, 'Tarczyński kabanosy',      '120g'),
  (449, 'Kabanos Drobimex',         '120g'),
  (450, 'Indykpol indyk',           '1kg'),
  (451, 'Krakus szynka',            '300g'),
  -- Snacks
  (452, 'Crunchips Paprika',        '140g'),
  (453, 'Crunchips Solone',         '140g'),
  (454, 'Star Chipsy',              '150g'),
  (455, 'Cheetos',                  '85g'),
  (456, 'Doritos',                  '180g'),
  (457, 'Paluszki Lajkonik',        '300g'),
  (458, 'Tartinki Wasa',            '200g'),
  -- Sweets
  (459, 'Wedel Ptasie Mleczko',     '380g'),
  (460, 'Wedel Pawełek',            '100g'),
  (461, 'Wawel Tiki Taki',          '280g'),
  (462, 'Wawel Michałki',           '280g'),
  (463, 'Goplana Grześki',          '36g'),
  (464, 'Goplana Czekolada Mleczna','100g'),
  (465, 'Delicje Szampańskie',      '147g'),
  (466, 'Krówki',                   '300g'),
  (467, 'Toffifee',                 '125g'),
  (468, 'Merci czekoladki',         '250g'),
  (469, 'Lindt Lindor',             '200g'),
  (470, 'Lindt Excellence',         '100g'),
  (471, 'Ritter Sport',             '100g'),
  (472, 'Tic Tac',                  '16g'),
  (473, 'Mentos',                   '38g'),
  (474, 'Skittles',                 '38g'),
  (475, 'Haribo Goldbären',         '100g'),
  -- Drinks
  (476, 'Frugo',                    '330ml'),
  (477, 'Kubuś Waterrr',            '330ml'),
  (478, 'Kubuś sok',                '1L'),
  (479, 'Cappy sok',                '330ml'),
  (480, 'Hoop Cola',                '1.5L'),
  (481, 'Tymbark Mleczny szejk',    '250ml'),
  (482, 'Pepsi Wild Cherry',        '0.5L'),
  (483, 'Lipton Ice Tea',           '1.5L'),
  (484, 'Nestea',                   '1.5L'),
  (485, 'Schweppes',                '1L'),
  (486, 'Muszynianka',              '1.5L'),
  (487, 'Nałęczowianka',            '1.5L'),
  (488, 'Kropla Beskidu',           '1.5L'),
  (489, 'Pepsi Twist',              '1.5L'),
  -- Beer
  (490, 'Tyskie',                   '0.5L'),
  (491, 'Żywiec piwo',              '0.5L'),
  (492, 'Lech',                     '0.5L'),
  (493, 'Warka',                    '0.5L'),
  (494, 'Książęce',                 '0.5L'),
  (495, 'Okocim',                   '0.5L'),
  (496, 'Heineken',                 '0.5L'),
  (497, 'Carlsberg',                '0.5L'),
  (498, 'Desperados',               '0.4L'),
  (499, 'Somersby',                 '0.4L'),
  -- Sauces / staples
  (500, 'Łowicki ketchup',          '450g'),
  (501, 'Pudliszki ketchup',        '480g'),
  (502, 'Pudliszki passata',        '500g'),
  (503, 'Develey musztarda',        '270g'),
  (504, 'Lubella makaron',          '500g'),
  (505, 'Malma makaron',            '500g'),
  (506, 'Britta makaron',           '500g'),
  (507, 'Łowicz dżem',              '280g'),
  (508, 'Łowicz konfitura',         '300g'),
  -- Frozen
  (509, 'Hortex frytki',            '1kg'),
  (510, 'Hortex truskawki mrożone', '450g'),
  (511, 'Iglotex pierogi',          '450g'),
  (512, 'Bonduelle kukurydza',      '340g'),
  (513, 'Pierogi Madej Wróbel',     '500g'),
  (514, 'Mrożone warzywa Hortex',   '450g'),
  -- Personal care
  (515, 'Nivea krem',               '75ml'),
  (516, 'Nivea żel pod prysznic',   '250ml'),
  (517, 'Garnier szampon',          '400ml'),
  (518, 'Schwarzkopf szampon',      '400ml'),
  (519, 'Head & Shoulders',         '400ml'),
  (520, 'Dove żel pod prysznic',    '250ml'),
  (521, 'Old Spice dezodorant',     '150ml'),
  (522, 'Rexona dezodorant',        '150ml'),
  (523, 'Colgate pasta',            '100ml'),
  (524, 'Signal pasta',             '75ml'),
  (525, 'Sensodyne pasta',          '75ml'),
  (526, 'Listerine',                '500ml'),
  (527, 'Gillette żyletki',         '4 szt.'),
  (528, 'Bella podpaski',           '10 szt.'),
  (529, 'Always podpaski',          '12 szt.'),
  -- Household
  (530, 'Persil proszek',           '3kg'),
  (531, 'Ariel proszek',            '3kg'),
  (532, 'Vizir kapsułki',           '30 szt.'),
  (533, 'Lenor płyn',               '1.5L'),
  (534, 'Domestos',                 '1.25L'),
  (535, 'Cif krem',                 '750ml'),
  (536, 'Cillit Bang',              '750ml'),
  (537, 'Ludwik płyn do naczyń',    '1L'),
  (538, 'Fairy płyn do naczyń',     '900ml'),
  (539, 'Pronto do mebli',          '250ml'),
  (540, 'Velvet papier toaletowy',  '8 rolek'),
  (541, 'Regina papier toaletowy',  '8 rolek'),
  (542, 'Foliopak worki',           '30 szt.')
ON CONFLICT DO NOTHING;

-- 2. Base prices (Biedronka reference, PLN).
WITH base_prices(product_id, base) AS (
  VALUES
    -- dairy
    (431, 12.99::numeric), (432, 9.49), (433, 4.99),
    (435, 6.99), (436, 5.99), (437, 2.49), (438, 2.79),
    (439, 2.69),            (441, 3.99), (442, 3.49),
    (443, 4.49), (444, 4.29), (445, 4.99),
    -- meat
    (446, 9.99), (447, 24.99), (448, 5.99), (449, 4.99),
    (450, 32.99), (451, 8.99),
    -- snacks
    (452, 6.99), (453, 6.99), (454, 5.49), (455, 4.99),
    (456, 9.99), (457, 4.99), (458, 7.99),
    -- sweets
    (459, 18.99), (460, 4.99), (461, 9.99), (462, 9.99),
    (463, 1.49), (464, 4.49), (465, 8.99), (466, 9.99),
    (467, 8.99), (468, 19.99), (469, 24.99), (470, 9.99),
    (471, 4.99), (472, 3.49), (473, 2.99), (474, 2.99), (475, 4.99),
    -- drinks
    (476, 2.99), (477, 2.79), (478, 5.99), (479, 2.99),
    (480, 5.49), (481, 3.49), (482, 3.99), (483, 6.99),
    (484, 6.49), (485, 6.99), (486, 1.99), (487, 1.79),
    (488, 1.69), (489, 5.99),
    -- beer
    (490, 3.49), (491, 3.49), (492, 3.49), (493, 3.29),
    (494, 3.79), (495, 3.29), (496, 4.49), (497, 4.29),
    (498, 5.49), (499, 5.49),
    -- sauces / staples
    (500, 4.99), (501, 5.49), (502, 3.99), (503, 4.49),
    (504, 4.49), (505, 3.99), (506, 3.79), (507, 5.99), (508, 6.49),
    -- frozen
    (509, 7.99), (510, 9.99), (511, 8.99), (512, 4.49),
    (513, 8.99), (514, 7.49),
    -- personal care
    (515, 14.99), (516, 8.99), (517, 14.99), (518, 16.99),
    (519, 19.99), (520, 9.99), (521, 12.99), (522, 11.99),
    (523, 8.99), (524, 6.49), (525, 13.99), (526, 14.99),
    (527, 24.99), (528, 6.99), (529, 8.99),
    -- household
    (530, 42.99), (531, 39.99), (532, 34.99), (533, 19.99),
    (534, 11.99), (535, 9.99), (536, 12.99), (537, 9.99),
    (538, 13.99), (539, 12.99), (540, 14.99), (541, 13.99), (542, 3.99)
),
-- Store multipliers vs Biedronka baseline (derived from historical data).
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

-- 3. Verification.
SELECT COUNT(*) AS new_products     FROM products WHERE id >= 431;
SELECT COUNT(*) AS new_price_rows   FROM prices
  WHERE product_id >= 431;
SELECT s.name, COUNT(*) AS rows
  FROM prices p JOIN stores s ON s.id = p.store_id
  WHERE p.product_id >= 431
  GROUP BY s.name
  ORDER BY s.name;
