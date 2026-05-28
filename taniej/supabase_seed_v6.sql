-- 100 snack products (251–350)
-- Run in Supabase SQL Editor

insert into products (id, name, unit) values
  -- Chips varieties
  (251, 'Chipsy paprykowe',             '130g'),
  (252, 'Chipsy solone',                '130g'),
  (253, 'Chipsy serowe',                '130g'),
  (254, 'Chipsy pikantne',              '130g'),
  (255, 'Chipsy cebulowe',              '130g'),
  (256, 'Chipsy tortilla',              '200g'),
  (257, 'Chipsy warzywne',              '80g'),
  (258, 'Chipsy batatowe',              '80g'),
  (259, 'Chipsy pełnoziarniste',        '130g'),
  (260, 'Chipsy o smaku szynki',        '130g'),
  -- Chocolate varieties
  (261, 'Czekolada mleczna',            '100g'),
  (262, 'Czekolada biała',              '100g'),
  (263, 'Czekolada z orzechami',        '100g'),
  (264, 'Czekolada z migdałami',        '100g'),
  (265, 'Czekolada z rodzynkami',       '100g'),
  (266, 'Czekolada deserowa 70%',       '100g'),
  (267, 'Czekolada karmelowa',          '100g'),
  (268, 'Czekolada z truskawkami',      '100g'),
  (269, 'Czekolada bez cukru',          '100g'),
  (270, 'Czekolada z kokosem',          '100g'),
  -- Chocolate bars
  (271, 'Baton z orzechami',            '50g'),
  (272, 'Baton karmelowy',              '50g'),
  (273, 'Baton kokosowy',               '50g'),
  (274, 'Baton waflowy',                '45g'),
  (275, 'Baton musli',                  '40g'),
  (276, 'Baton proteinowy',             '60g'),
  (277, 'Baton owocowy',                '40g'),
  (278, 'Baton zbożowy z orzechami',    '45g'),
  -- Candy & sweets
  (279, 'Żelki misie',                  '100g'),
  (280, 'Żelki kwaśne',                 '100g'),
  (281, 'Żelki cola',                   '100g'),
  (282, 'Cukierki krówki',              '100g'),
  (283, 'Cukierki miętowe',             '50g'),
  (284, 'Cukierki owocowe',             '100g'),
  (285, 'Lizaki',                       '5 szt.'),
  (286, 'Guma do żucia',                '17g'),
  (287, 'Landrynki',                    '100g'),
  (288, 'Dropsy miętowe',               '50g'),
  (289, 'Karmelki krówkowe',            '100g'),
  (290, 'Żelki witaminowe',             '60g'),
  -- Cookies & biscuits
  (291, 'Ciastka maślane',              '150g'),
  (292, 'Ciastka owsiane',              '200g'),
  (293, 'Ciastka z kremem',             '150g'),
  (294, 'Ciastka kakaowe',              '150g'),
  (295, 'Herbatniki',                   '200g'),
  (296, 'Ciastka kokosowe',             '150g'),
  (297, 'Wafle z kremem',               '200g'),
  (298, 'Wafle czekoladowe',            '200g'),
  (299, 'Ciastka z dżemem',             '200g'),
  (300, 'Ciastka zbożowe',              '200g'),
  (301, 'Ciastka z owocami',            '150g'),
  (302, 'Delicje',                      '175g'),
  -- Nuts & seeds
  (303, 'Orzeszki ziemne',              '200g'),
  (304, 'Orzeszki w czekoladzie',       '200g'),
  (305, 'Orzeszki miodowe',             '150g'),
  (306, 'Orzechy laskowe',              '200g'),
  (307, 'Orzechy makadamia',            '150g'),
  (308, 'Mix bakaliów',                 '200g'),
  (309, 'Słonecznik prażony',           '200g'),
  (310, 'Dynia prażona',                '100g'),
  (311, 'Kokos wiórki',                 '100g'),
  -- Dried fruits
  (312, 'Suszone morele',               '200g'),
  (313, 'Suszone śliwki',               '200g'),
  (314, 'Suszone mango',                '100g'),
  (315, 'Suszone banany',               '100g'),
  (316, 'Suszone jabłka',               '100g'),
  (317, 'Suszone figi',                 '200g'),
  (318, 'Daktyle w czekoladzie',        '100g'),
  -- Popcorn varieties
  (319, 'Popcorn słony',                '100g'),
  (320, 'Popcorn maślany',              '100g'),
  (321, 'Popcorn karmelowy',            '100g'),
  (322, 'Popcorn serowy',               '100g'),
  -- Ice cream
  (323, 'Lody czekoladowe',             '500ml'),
  (324, 'Lody waniliowe',               '500ml'),
  (325, 'Lody truskawkowe',             '500ml'),
  (326, 'Lody Magnum style',            '110ml'),
  (327, 'Lody rożek',                   '110ml'),
  (328, 'Sorbet owocowy',               '500ml'),
  -- Rice & corn snacks
  (329, 'Wafle ryżowe solone',          '130g'),
  (330, 'Chrupki ryżowe',               '100g'),
  (331, 'Puffed corn',                  '100g'),
  (332, 'Grissini',                     '125g'),
  -- Meat snacks
  (333, 'Kabanosy',                     '100g'),
  (334, 'Paluszki mięsne',              '100g'),
  (335, 'Suszone mięso wołowe',         '50g'),
  (336, 'Biltong',                      '50g'),
  -- Crackers
  (337, 'Krakersy pełnoziarniste',      '100g'),
  (338, 'Krakersy z ziarnami',          '100g'),
  (339, 'Krakersy ryżowe',              '100g'),
  -- Granola & bars
  (340, 'Granola',                      '400g'),
  (341, 'Baton daktylowy',              '45g'),
  -- Salty snacks
  (342, 'Precelki solone',              '200g'),
  (343, 'Paluszki z sezamem',           '200g'),
  (344, 'Chipsy pita',                  '150g'),
  (345, 'Chrupki zbożowe',              '100g'),
  -- Special sweets
  (346, 'Pianka cukrowa',               '100g'),
  (347, 'Chałwa',                       '200g'),
  (348, 'Nugat',                        '100g'),
  -- Bakery snacks
  (349, 'Muffin czekoladowy',           '1 szt.'),
  (350, 'Brownie',                      '1 szt.');

-- Biedronka (store_id=1)
insert into prices (store_id, product_id, price) values
  (1, 251, 4.99), (1, 252, 4.49), (1, 253, 4.99), (1, 254, 4.99),
  (1, 255, 4.49), (1, 256, 5.99), (1, 257, 5.99), (1, 258, 6.49),
  (1, 259, 4.99), (1, 260, 4.49), (1, 261, 3.49), (1, 262, 3.99),
  (1, 263, 3.99), (1, 264, 4.49), (1, 265, 3.99), (1, 266, 4.99),
  (1, 267, 4.49), (1, 268, 3.99), (1, 269, 5.99), (1, 270, 3.99),
  (1, 271, 2.99), (1, 272, 2.99), (1, 273, 2.99), (1, 274, 2.49),
  (1, 275, 2.49), (1, 276, 5.99), (1, 277, 2.49), (1, 278, 2.49),
  (1, 279, 3.49), (1, 280, 3.49), (1, 281, 3.49), (1, 282, 4.99),
  (1, 283, 2.99), (1, 284, 3.99), (1, 285, 3.49), (1, 286, 2.99),
  (1, 287, 3.99), (1, 288, 2.99), (1, 289, 4.99), (1, 290, 6.99),
  (1, 291, 4.99), (1, 292, 4.99), (1, 293, 4.49), (1, 294, 4.49),
  (1, 295, 3.99), (1, 296, 4.99), (1, 297, 4.99), (1, 298, 4.99),
  (1, 299, 5.49), (1, 300, 4.99), (1, 301, 4.99), (1, 302, 5.99),
  (1, 303, 4.99), (1, 304, 6.99), (1, 305, 5.99), (1, 306, 7.99),
  (1, 307, 12.99),(1, 308, 7.99), (1, 309, 3.99), (1, 310, 4.99),
  (1, 311, 3.99), (1, 312, 7.99), (1, 313, 6.99), (1, 314, 7.99),
  (1, 315, 6.99), (1, 316, 6.99), (1, 317, 8.99), (1, 318, 6.99),
  (1, 319, 3.99), (1, 320, 4.49), (1, 321, 5.49), (1, 322, 4.99),
  (1, 323, 8.99), (1, 324, 7.99), (1, 325, 7.99), (1, 326, 3.99),
  (1, 327, 3.49), (1, 328, 8.99), (1, 329, 4.49), (1, 330, 3.99),
  (1, 331, 3.49), (1, 332, 3.99), (1, 333, 6.99), (1, 334, 5.99),
  (1, 335, 9.99), (1, 336, 10.99),(1, 337, 4.99), (1, 338, 5.49),
  (1, 339, 4.49), (1, 340, 9.99), (1, 341, 3.99), (1, 342, 3.99),
  (1, 343, 3.99), (1, 344, 5.99), (1, 345, 3.49), (1, 346, 3.99),
  (1, 347, 7.99), (1, 348, 5.99), (1, 349, 3.99), (1, 350, 4.99);

-- All other stores via multipliers
insert into prices (store_id, product_id, price)
select 2, product_id, round((price * 0.94)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;

insert into prices (store_id, product_id, price)
select 3, product_id, round((price * 1.07)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;

insert into prices (store_id, product_id, price)
select 4, product_id, round((price * 0.92)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;

insert into prices (store_id, product_id, price)
select 5, product_id, round((price * 0.97)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;

insert into prices (store_id, product_id, price)
select 6, product_id, round((price * 1.09)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;

insert into prices (store_id, product_id, price)
select 7, product_id, round((price * 1.13)::numeric, 2)
from prices where store_id = 1 and product_id between 251 and 350;
