-- 50 more products (201–250)
-- Run in Supabase SQL Editor

insert into products (id, name, unit) values
  -- Snacks
  (201, 'Nachos',                  '200g'),
  (202, 'Krakersy',                '100g'),
  (203, 'Paluszki chlebowe',       '200g'),
  (204, 'Wafelki',                 '150g'),
  (205, 'Wafle ryżowe',            '130g'),
  (206, 'Chrupki kukurydziane',    '100g'),
  (207, 'Orzeszki solone',         '200g'),
  (208, 'Pistacje',                '150g'),
  (209, 'Mix orzechów',            '200g'),
  (210, 'Biszkopty',               '200g'),
  -- Sweets & desserts
  (211, 'Budyń',                   '40g'),
  (212, 'Kisiel',                  '77g'),
  (213, 'Galaretka',               '75g'),
  (214, 'Pierniki',                '400g'),
  (215, 'Wafle',                   '200g'),
  (216, 'Ptasie mleczko',          '340g'),
  (217, 'Lody na patyku',          '110ml'),
  (218, 'Karmelki',                '100g'),
  (219, 'Żurawina w czekoladzie',  '100g'),
  (220, 'Marcepan',                '100g'),
  -- Sauces & extras
  (221, 'Sos tzatziki',            '200g'),
  (222, 'Sos chilli',              '200ml'),
  (223, 'Tahini',                  '250g'),
  (224, 'Tofu',                    '200g'),
  (225, 'Sos Worcester',           '150ml'),
  (226, 'Sos rybny',               '200ml'),
  (227, 'Sos hoisin',              '200ml'),
  (228, 'Pasta curry',             '100g'),
  -- Convenience / ready meals
  (229, 'Zupka instant',           '65g'),
  (230, 'Makaron instant',         '70g'),
  (231, 'Tortilla wrap',           '8 szt.'),
  (232, 'Naleśniki mrożone',       '400g'),
  (233, 'Placki ziemniaczane mrożone', '400g'),
  (234, 'Kopytka mrożone',         '500g'),
  (235, 'Gołąbki mrożone',         '500g'),
  -- Drinks
  (236, 'Red Bull',                '250ml'),
  (237, 'Sprite',                  '1.5L'),
  (238, 'Fanta',                   '1.5L'),
  (239, 'Pepsi',                   '1.5L'),
  (240, 'Sok multivitaminowy',     '1L'),
  (241, 'Syrop owocowy',           '400ml'),
  (242, 'Napój izotoniczny',       '500ml'),
  -- More dairy
  (243, 'Ser topiony',             '140g'),
  (244, 'Koktajl mleczny',         '400ml'),
  (245, 'Śmietanka UHT',           '200ml'),
  -- Pet & baby
  (246, 'Karma dla psa',           '400g'),
  (247, 'Karma dla kota',          '400g'),
  -- Extras
  (248, 'Drożdżówka',              '1 szt.'),
  (249, 'Pączek',                  '1 szt.'),
  (250, 'Croissant',               '1 szt.');

-- Biedronka (store_id=1)
insert into prices (store_id, product_id, price) values
  (1, 201, 5.99),
  (1, 202, 3.99),
  (1, 203, 3.49),
  (1, 204, 3.99),
  (1, 205, 4.99),
  (1, 206, 3.49),
  (1, 207, 4.99),
  (1, 208, 9.99),
  (1, 209, 7.99),
  (1, 210, 4.99),
  (1, 211, 1.49),
  (1, 212, 1.49),
  (1, 213, 1.49),
  (1, 214, 7.99),
  (1, 215, 4.49),
  (1, 216, 11.99),
  (1, 217, 2.99),
  (1, 218, 3.49),
  (1, 219, 5.99),
  (1, 220, 5.99),
  (1, 221, 5.99),
  (1, 222, 5.49),
  (1, 223, 12.99),
  (1, 224, 7.99),
  (1, 225, 8.99),
  (1, 226, 7.99),
  (1, 227, 8.99),
  (1, 228, 6.99),
  (1, 229, 1.99),
  (1, 230, 2.49),
  (1, 231, 5.99),
  (1, 232, 7.99),
  (1, 233, 7.99),
  (1, 234, 8.99),
  (1, 235, 12.99),
  (1, 236, 5.99),
  (1, 237, 4.99),
  (1, 238, 4.99),
  (1, 239, 4.99),
  (1, 240, 5.49),
  (1, 241, 6.99),
  (1, 242, 3.99),
  (1, 243, 5.99),
  (1, 244, 3.99),
  (1, 245, 2.99),
  (1, 246, 5.99),
  (1, 247, 4.99),
  (1, 248, 1.99),
  (1, 249, 2.49),
  (1, 250, 2.99);

-- All other stores via multipliers
insert into prices (store_id, product_id, price)
select 2, product_id, round((price * 0.94)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;

insert into prices (store_id, product_id, price)
select 3, product_id, round((price * 1.07)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;

insert into prices (store_id, product_id, price)
select 4, product_id, round((price * 0.92)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;

insert into prices (store_id, product_id, price)
select 5, product_id, round((price * 0.97)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;

insert into prices (store_id, product_id, price)
select 6, product_id, round((price * 1.09)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;

insert into prices (store_id, product_id, price)
select 7, product_id, round((price * 1.13)::numeric, 2)
from prices where store_id = 1 and product_id between 201 and 250;
