-- Add 4 new stores
-- Run in Supabase SQL Editor

insert into stores (id, name, logo) values
  (4, 'Aldi',      '🔵'),
  (5, 'Netto',     '🟡'),
  (6, 'Auchan',    '🟠'),
  (7, 'Carrefour', '⭐');

-- Aldi: ~8% cheaper than Biedronka
insert into prices (store_id, product_id, price)
select 4, product_id, round((price * 0.92)::numeric, 2)
from prices where store_id = 1;

-- Netto: ~3% cheaper than Biedronka
insert into prices (store_id, product_id, price)
select 5, product_id, round((price * 0.97)::numeric, 2)
from prices where store_id = 1;

-- Auchan: ~9% more expensive than Biedronka
insert into prices (store_id, product_id, price)
select 6, product_id, round((price * 1.09)::numeric, 2)
from prices where store_id = 1;

-- Carrefour: ~13% more expensive than Biedronka
insert into prices (store_id, product_id, price)
select 7, product_id, round((price * 1.13)::numeric, 2)
from prices where store_id = 1;
