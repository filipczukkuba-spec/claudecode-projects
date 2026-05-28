-- Stores
create table stores (
  id serial primary key,
  name text not null,
  logo text
);

-- Products
create table products (
  id serial primary key,
  name text not null,
  unit text
);

-- Prices (one row per store+product combo)
create table prices (
  id serial primary key,
  store_id integer references stores(id),
  product_id integer references products(id),
  price numeric(8,2),
  updated_at timestamptz default now(),
  unique(store_id, product_id)
);

-- Seed stores
insert into stores (name, logo) values
  ('Biedronka', '🛒'),
  ('Lidl', '🛍️'),
  ('Kaufland', '🏪');

-- Seed products
insert into products (name, unit) values
  ('Mleko', '1L'),
  ('Chleb', '1 bochenek'),
  ('Masło', '200g'),
  ('Jajka', '10 szt.'),
  ('Banany', '1kg'),
  ('Jabłka', '1kg'),
  ('Pomidory', '1kg'),
  ('Ziemniaki', '1kg'),
  ('Marchew', '1kg'),
  ('Cebula', '1kg'),
  ('Ser żółty', '1kg'),
  ('Jogurt naturalny', '400g'),
  ('Śmietana', '200ml'),
  ('Ryż', '1kg'),
  ('Makaron', '500g'),
  ('Mąka', '1kg'),
  ('Cukier', '1kg'),
  ('Olej słonecznikowy', '1L'),
  ('Ketchup', '450g'),
  ('Pierś z kurczaka', '1kg'),
  ('Kiełbasa', '1kg'),
  ('Parówki', '500g'),
  ('Tuńczyk w puszce', '170g'),
  ('Woda mineralna', '1.5L'),
  ('Sok pomarańczowy', '1L'),
  ('Płatki owsiane', '500g'),
  ('Majonez', '400ml'),
  ('Musztarda', '185g'),
  ('Papier toaletowy', '8 rolek'),
  ('Płyn do naczyń', '1L');

-- Seed prices (real approximate Polish market prices as of May 2026)
-- Biedronka (store_id=1)
insert into prices (store_id, product_id, price) values
  (1, 1, 3.49),   -- Mleko
  (1, 2, 4.99),   -- Chleb
  (1, 3, 7.99),   -- Masło
  (1, 4, 13.99),  -- Jajka
  (1, 5, 4.99),   -- Banany
  (1, 6, 3.99),   -- Jabłka
  (1, 7, 5.99),   -- Pomidory
  (1, 8, 2.49),   -- Ziemniaki
  (1, 9, 3.49),   -- Marchew
  (1, 10, 2.99),  -- Cebula
  (1, 11, 29.99), -- Ser żółty
  (1, 12, 2.89),  -- Jogurt
  (1, 13, 2.49),  -- Śmietana
  (1, 14, 4.49),  -- Ryż
  (1, 15, 2.99),  -- Makaron
  (1, 16, 3.49),  -- Mąka
  (1, 17, 4.99),  -- Cukier
  (1, 18, 7.99),  -- Olej
  (1, 19, 4.99),  -- Ketchup
  (1, 20, 19.99), -- Pierś z kurczaka
  (1, 21, 22.99), -- Kiełbasa
  (1, 22, 8.99),  -- Parówki
  (1, 23, 5.49),  -- Tuńczyk
  (1, 24, 2.99),  -- Woda
  (1, 25, 5.99),  -- Sok
  (1, 26, 4.29),  -- Płatki owsiane
  (1, 27, 6.99),  -- Majonez
  (1, 28, 3.49),  -- Musztarda
  (1, 29, 14.99), -- Papier toaletowy
  (1, 30, 6.99);  -- Płyn do naczyń

-- Lidl (store_id=2)
insert into prices (store_id, product_id, price) values
  (2, 1, 3.29),
  (2, 2, 4.49),
  (2, 3, 8.49),
  (2, 4, 12.99),
  (2, 5, 4.49),
  (2, 6, 3.79),
  (2, 7, 5.49),
  (2, 8, 2.29),
  (2, 9, 3.29),
  (2, 10, 2.79),
  (2, 11, 27.99),
  (2, 12, 2.69),
  (2, 13, 2.29),
  (2, 14, 3.99),
  (2, 15, 2.79),
  (2, 16, 3.29),
  (2, 17, 4.79),
  (2, 18, 7.49),
  (2, 19, 4.79),
  (2, 20, 18.99),
  (2, 21, 21.99),
  (2, 22, 8.49),
  (2, 23, 4.99),
  (2, 24, 2.79),
  (2, 25, 5.49),
  (2, 26, 3.99),
  (2, 27, 6.49),
  (2, 28, 3.29),
  (2, 29, 13.99),
  (2, 30, 6.49);

-- Kaufland (store_id=3)
insert into prices (store_id, product_id, price) values
  (3, 1, 3.59),
  (3, 2, 5.29),
  (3, 3, 8.29),
  (3, 4, 14.49),
  (3, 5, 5.29),
  (3, 6, 4.29),
  (3, 7, 6.29),
  (3, 8, 2.69),
  (3, 9, 3.69),
  (3, 10, 3.19),
  (3, 11, 31.99),
  (3, 12, 2.99),
  (3, 13, 2.69),
  (3, 14, 4.69),
  (3, 15, 3.19),
  (3, 16, 3.69),
  (3, 17, 5.29),
  (3, 18, 8.29),
  (3, 19, 5.29),
  (3, 20, 20.99),
  (3, 21, 23.99),
  (3, 22, 9.49),
  (3, 23, 5.99),
  (3, 24, 3.19),
  (3, 25, 6.29),
  (3, 26, 4.69),
  (3, 27, 7.29),
  (3, 28, 3.79),
  (3, 29, 15.99),
  (3, 30, 7.29);
