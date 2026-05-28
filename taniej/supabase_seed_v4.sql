-- 60 new products (141–200)
-- Run in Supabase SQL Editor

insert into products (id, name, unit) values
  -- Dairy alternatives
  (141, 'Mleko sojowe',          '1L'),
  (142, 'Mleko owsiane',         '1L'),
  (143, 'Mleko migdałowe',       '1L'),
  (144, 'Śmietana 30%',          '200ml'),
  (145, 'Serek Philadelphia',    '150g'),
  (146, 'Ser Gouda',             '200g'),
  (147, 'Ser Edam',              '200g'),
  -- Frozen
  (148, 'Lody',                  '500ml'),
  (149, 'Mrożona pizza',         '1 szt.'),
  (150, 'Mrożone frytki',        '1kg'),
  (151, 'Mrożone warzywa mix',   '400g'),
  (152, 'Mrożone truskawki',     '500g'),
  (153, 'Pierogi mrożone',       '500g'),
  -- Meat & fish
  (154, 'Filet z indyka',        '1kg'),
  (155, 'Wątroba drobiowa',      '500g'),
  (156, 'Śledź',                 '300g'),
  (157, 'Sardynki w puszce',     '120g'),
  (158, 'Paluszki rybne',        '400g'),
  -- Vegetables
  (159, 'Batat',                 '1kg'),
  (160, 'Szparagi',              '300g'),
  (161, 'Pieczarki',             '400g'),
  -- Fruits
  (162, 'Kiwi',                  '1kg'),
  (163, 'Grejpfrut',             '1kg'),
  (164, 'Śliwki',                '1kg'),
  (165, 'Nektarynki',            '1kg'),
  (166, 'Brzoskwinie',           '1kg'),
  -- Nuts & seeds
  (167, 'Orzechy włoskie',       '200g'),
  (168, 'Orzechy nerkowca',      '150g'),
  (169, 'Migdały',               '200g'),
  (170, 'Rodzynki',              '200g'),
  (171, 'Nasiona chia',          '200g'),
  (172, 'Siemię lniane',         '500g'),
  -- Sauces & condiments
  (173, 'Sos BBQ',               '300ml'),
  (174, 'Hummus',                '200g'),
  (175, 'Pesto',                 '190g'),
  (176, 'Ocet jabłkowy',         '500ml'),
  -- Health foods
  (177, 'Komosa ryżowa',         '500g'),
  (178, 'Otręby pszenne',        '500g'),
  -- Drinks
  (179, 'Herbata zielona',       '50 torebek'),
  (180, 'Kawa instant',          '100g'),
  (181, 'Woda gazowana',         '1.5L'),
  (182, 'Piwo',                  '0.5L'),
  (183, 'Wino',                  '0.75L'),
  -- Bakery
  (184, 'Bagietka',              '1 szt.'),
  (185, 'Rogaliki',              '6 szt.'),
  (186, 'Pumpernikiel',          '500g'),
  -- Grains & pasta
  (187, 'Kasza bulgur',          '500g'),
  (188, 'Ryż jaśminowy',         '1kg'),
  (189, 'Ryż basmati',           '1kg'),
  (190, 'Makaron lasagne',       '500g'),
  -- Convenience
  (191, 'Zupa w proszku',        '60g'),
  -- Hygiene
  (192, 'Szampon',               '400ml'),
  (193, 'Mydło w kostce',        '100g'),
  (194, 'Pasta do zębów',        '75ml'),
  (195, 'Płyn do podłóg',        '1L'),
  (196, 'Proszek do zmywarki',   '1kg'),
  -- Snacks
  (197, 'Baton czekoladowy',     '50g'),
  (198, 'Żelki',                 '100g'),
  (199, 'Popcorn',               '100g'),
  (200, 'Precelki',              '150g');

-- Biedronka (store_id=1)
insert into prices (store_id, product_id, price) values
  (1, 141, 5.99),
  (1, 142, 7.99),
  (1, 143, 9.99),
  (1, 144, 3.49),
  (1, 145, 7.99),
  (1, 146, 6.99),
  (1, 147, 6.49),
  (1, 148, 7.99),
  (1, 149, 12.99),
  (1, 150, 6.99),
  (1, 151, 4.99),
  (1, 152, 5.99),
  (1, 153, 9.99),
  (1, 154, 18.99),
  (1, 155, 6.99),
  (1, 156, 8.99),
  (1, 157, 3.99),
  (1, 158, 9.99),
  (1, 159, 5.99),
  (1, 160, 7.99),
  (1, 161, 4.99),
  (1, 162, 6.99),
  (1, 163, 4.99),
  (1, 164, 5.99),
  (1, 165, 6.99),
  (1, 166, 6.99),
  (1, 167, 8.99),
  (1, 168, 11.99),
  (1, 169, 9.99),
  (1, 170, 4.99),
  (1, 171, 9.99),
  (1, 172, 4.99),
  (1, 173, 6.99),
  (1, 174, 7.99),
  (1, 175, 9.99),
  (1, 176, 4.99),
  (1, 177, 12.99),
  (1, 178, 3.99),
  (1, 179, 6.99),
  (1, 180, 9.99),
  (1, 181, 2.99),
  (1, 182, 3.49),
  (1, 183, 19.99),
  (1, 184, 2.99),
  (1, 185, 4.99),
  (1, 186, 5.99),
  (1, 187, 4.99),
  (1, 188, 7.99),
  (1, 189, 8.99),
  (1, 190, 3.99),
  (1, 191, 2.49),
  (1, 192, 12.99),
  (1, 193, 2.99),
  (1, 194, 5.99),
  (1, 195, 7.99),
  (1, 196, 19.99),
  (1, 197, 2.49),
  (1, 198, 3.49),
  (1, 199, 3.99),
  (1, 200, 3.49);

-- Lidl (store_id=2) — ~6% cheaper than Biedronka
insert into prices (store_id, product_id, price)
select 2, product_id, round((price * 0.94)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;

-- Kaufland (store_id=3) — ~7% more expensive
insert into prices (store_id, product_id, price)
select 3, product_id, round((price * 1.07)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;

-- Aldi — ~8% cheaper
insert into prices (store_id, product_id, price)
select 4, product_id, round((price * 0.92)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;

-- Netto — ~3% cheaper
insert into prices (store_id, product_id, price)
select 5, product_id, round((price * 0.97)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;

-- Auchan — ~9% more expensive
insert into prices (store_id, product_id, price)
select 6, product_id, round((price * 1.09)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;

-- Carrefour — ~13% more expensive
insert into prices (store_id, product_id, price)
select 7, product_id, round((price * 1.13)::numeric, 2)
from prices where store_id = 1 and product_id between 141 and 200;
