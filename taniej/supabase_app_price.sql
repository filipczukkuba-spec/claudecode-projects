-- Add app_price column to prices table
ALTER TABLE prices ADD COLUMN IF NOT EXISTS app_price DECIMAL(10,2) DEFAULT NULL;

-- Example: Lidl Plus price for mleko
-- UPDATE prices p
-- SET app_price = 1.49
-- WHERE store_id = (SELECT id FROM stores WHERE name = 'Lidl')
--   AND product_id = (SELECT id FROM products WHERE name ILIKE '%mleko%' LIMIT 1);
