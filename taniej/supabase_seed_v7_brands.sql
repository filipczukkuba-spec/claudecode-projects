-- Branded products (351–430)
-- Run in Supabase SQL Editor

insert into products (id, name, unit) values
  -- Lay's chips
  (351, 'Lay''s Papryka',              '130g'),
  (352, 'Lay''s Solone',               '130g'),
  (353, 'Lay''s Zesty BBQ',            '130g'),
  (354, 'Lay''s Ser i Cebula',         '130g'),
  (355, 'Lay''s Max Papryka',          '120g'),
  -- Pringles
  (356, 'Pringles Original',           '165g'),
  (357, 'Pringles Paprika',            '165g'),
  (358, 'Pringles Sour Cream',         '165g'),
  (359, 'Pringles BBQ',                '165g'),
  -- Chocolate bars
  (360, 'Snickers',                    '50g'),
  (361, 'Twix',                        '50g'),
  (362, 'Mars',                        '51g'),
  (363, 'Bounty',                      '57g'),
  (364, 'Kit Kat',                     '41g'),
  (365, 'Kinder Bueno',                '43g'),
  (366, 'Kinder czekolada',            '100g'),
  (367, 'Milky Way',                   '26g'),
  (368, 'Lion',                        '42g'),
  (369, 'Prince Polo',                 '35g'),
  -- Chocolate tablets
  (370, 'Milka Mleczna',               '100g'),
  (371, 'Milka Oreo',                  '100g'),
  (372, 'Milka Karmel',                '100g'),
  (373, 'Milka Strawberry',            '100g'),
  (374, 'Milka White',                 '100g'),
  (375, 'Wedel Czekolada',             '100g'),
  (376, 'Wawel Czekolada Mleczna',     '100g'),
  (377, 'Ferrero Rocher',              '3 szt.'),
  (378, 'Raffaello',                   '3 szt.'),
  (379, 'Toblerone',                   '100g'),
  (380, 'After Eight',                 '200g'),
  -- Biscuits
  (381, 'Oreo',                        '176g'),
  (382, 'Oreo Double Stuf',            '157g'),
  (383, 'Delicje',                     '175g'),
  (384, 'Leibniz',                     '200g'),
  (385, 'BelVita',                     '225g'),
  (386, 'Digestive McVitie''s',        '400g'),
  -- Dairy brands
  (387, 'Activia jogurt',              '150g'),
  (388, 'Actimel',                     '100ml'),
  (389, 'Danio serek',                 '140g'),
  (390, 'Zott Monte',                  '100g'),
  (391, 'Łaciate mleko',               '1L'),
  (392, 'Piątnica śmietana',           '200ml'),
  (393, 'President masło',             '200g'),
  (394, 'Alpro sojowe',                '1L'),
  (395, 'Oatly owsiane',               '1L'),
  -- Drinks brands
  (396, 'Coca-Cola',                   '0.5L'),
  (397, 'Coca-Cola Zero',              '0.5L'),
  (398, 'Pepsi Max',                   '0.5L'),
  (399, 'Red Bull',                    '250ml'),
  (400, 'Monster Energy',              '500ml'),
  (401, 'Tiger Energy',                '250ml'),
  (402, 'Tymbark sok',                 '1L'),
  (403, 'Hortex sok',                  '1L'),
  (404, 'Cisowianka',                  '1.5L'),
  (405, 'Żywiec Zdrój',                '1.5L'),
  -- Spreads
  (406, 'Nutella',                     '200g'),
  (407, 'Lotus Biscoff',               '400g'),
  (408, 'Skippy Peanut Butter',        '340g'),
  -- Ice cream brands
  (409, 'Magnum Classic',              '110ml'),
  (410, 'Magnum Almond',               '110ml'),
  (411, 'Cornetto',                    '120ml'),
  (412, 'Ben & Jerry''s',              '465ml'),
  (413, 'Koral lody',                  '1L'),
  -- Instant noodles
  (414, 'Knorr zupa',                  '68g'),
  (415, 'Maggi zupa',                  '68g'),
  (416, 'Winiary zupa',                '68g'),
  -- Sauces brands
  (417, 'Winiary majonez',             '400ml'),
  (418, 'Kielecki majonez',            '400ml'),
  (419, 'Heinz ketchup',               '450g'),
  (420, 'Hellmann''s majonez',         '400ml');

-- Biedronka (store_id=1)
insert into prices (store_id, product_id, price) values
  (1, 351, 5.99),  -- Lay's Papryka
  (1, 352, 5.49),  -- Lay's Solone
  (1, 353, 5.99),  -- Lay's BBQ
  (1, 354, 5.99),  -- Lay's Ser i Cebula
  (1, 355, 6.49),  -- Lay's Max
  (1, 356, 8.99),  -- Pringles Original
  (1, 357, 8.99),  -- Pringles Paprika
  (1, 358, 8.99),  -- Pringles Sour Cream
  (1, 359, 8.99),  -- Pringles BBQ
  (1, 360, 2.99),  -- Snickers
  (1, 361, 2.99),  -- Twix
  (1, 362, 2.99),  -- Mars
  (1, 363, 2.99),  -- Bounty
  (1, 364, 2.99),  -- Kit Kat
  (1, 365, 3.49),  -- Kinder Bueno
  (1, 366, 5.99),  -- Kinder czekolada
  (1, 367, 1.99),  -- Milky Way
  (1, 368, 2.49),  -- Lion
  (1, 369, 1.49),  -- Prince Polo
  (1, 370, 4.49),  -- Milka Mleczna
  (1, 371, 5.49),  -- Milka Oreo
  (1, 372, 4.99),  -- Milka Karmel
  (1, 373, 4.99),  -- Milka Strawberry
  (1, 374, 4.99),  -- Milka White
  (1, 375, 3.99),  -- Wedel
  (1, 376, 3.49),  -- Wawel
  (1, 377, 6.99),  -- Ferrero Rocher
  (1, 378, 6.99),  -- Raffaello
  (1, 379, 7.99),  -- Toblerone
  (1, 380, 12.99), -- After Eight
  (1, 381, 7.99),  -- Oreo
  (1, 382, 8.99),  -- Oreo Double Stuf
  (1, 383, 5.99),  -- Delicje
  (1, 384, 6.99),  -- Leibniz
  (1, 385, 7.99),  -- BelVita
  (1, 386, 9.99),  -- Digestive
  (1, 387, 2.99),  -- Activia
  (1, 388, 2.49),  -- Actimel
  (1, 389, 2.99),  -- Danio
  (1, 390, 2.99),  -- Zott Monte
  (1, 391, 3.69),  -- Łaciate
  (1, 392, 3.49),  -- Piątnica
  (1, 393, 8.99),  -- President masło
  (1, 394, 6.99),  -- Alpro
  (1, 395, 7.99),  -- Oatly
  (1, 396, 3.99),  -- Coca-Cola
  (1, 397, 3.99),  -- Coca-Cola Zero
  (1, 398, 3.79),  -- Pepsi Max
  (1, 399, 5.99),  -- Red Bull
  (1, 400, 6.99),  -- Monster
  (1, 401, 3.99),  -- Tiger
  (1, 402, 4.99),  -- Tymbark
  (1, 403, 4.79),  -- Hortex
  (1, 404, 2.49),  -- Cisowianka
  (1, 405, 2.29),  -- Żywiec Zdrój
  (1, 406, 7.99),  -- Nutella 200g
  (1, 407, 14.99), -- Lotus Biscoff
  (1, 408, 12.99), -- Skippy
  (1, 409, 5.99),  -- Magnum Classic
  (1, 410, 6.49),  -- Magnum Almond
  (1, 411, 4.99),  -- Cornetto
  (1, 412, 24.99), -- Ben & Jerry's
  (1, 413, 9.99),  -- Koral
  (1, 414, 2.49),  -- Knorr zupa
  (1, 415, 2.49),  -- Maggi zupa
  (1, 416, 2.29),  -- Winiary zupa
  (1, 417, 6.99),  -- Winiary majonez
  (1, 418, 7.49),  -- Kielecki majonez
  (1, 419, 6.99),  -- Heinz ketchup
  (1, 420, 8.99);  -- Hellmann's

-- Lidl — some branded products not sold there, use similar prices
insert into prices (store_id, product_id, price)
select 2, product_id, round((price * 0.97)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;

-- Kaufland
insert into prices (store_id, product_id, price)
select 3, product_id, round((price * 1.05)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;

-- Aldi
insert into prices (store_id, product_id, price)
select 4, product_id, round((price * 0.95)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;

-- Netto
insert into prices (store_id, product_id, price)
select 5, product_id, round((price * 0.98)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;

-- Auchan
insert into prices (store_id, product_id, price)
select 6, product_id, round((price * 1.03)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;

-- Carrefour
insert into prices (store_id, product_id, price)
select 7, product_id, round((price * 1.06)::numeric, 2)
from prices where store_id = 1 and product_id between 351 and 420;
