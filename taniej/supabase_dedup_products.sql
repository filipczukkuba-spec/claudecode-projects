-- Find and merge duplicate products (same name, different ids).
-- Keeps the LOWER id and remaps all foreign-key references to it.

-- 1. PREVIEW: list duplicates
SELECT LOWER(name) AS name_norm, COUNT(*) AS dups, ARRAY_AGG(id ORDER BY id) AS ids
FROM products
GROUP BY LOWER(name)
HAVING COUNT(*) > 1;

-- 2. MERGE: for each duplicate group, point all FKs to the lowest id
--    and delete the higher-id rows.
WITH dup_groups AS (
  SELECT LOWER(name) AS name_norm,
         MIN(id)     AS keep_id,
         ARRAY_AGG(id ORDER BY id) AS all_ids
  FROM products
  GROUP BY LOWER(name)
  HAVING COUNT(*) > 1
),
remaps AS (
  SELECT p.id AS old_id, dg.keep_id
  FROM dup_groups dg
  JOIN products p ON LOWER(p.name) = dg.name_norm AND p.id <> dg.keep_id
)
-- Remap prices: delete the row if (keep_id, store_id) already exists, else update.
DELETE FROM prices p
USING remaps r
WHERE p.product_id = r.old_id
  AND EXISTS (SELECT 1 FROM prices q WHERE q.product_id = r.keep_id AND q.store_id = p.store_id);

UPDATE prices p
SET    product_id = r.keep_id
FROM (
  WITH dup_groups AS (
    SELECT LOWER(name) AS name_norm, MIN(id) AS keep_id
    FROM products GROUP BY LOWER(name) HAVING COUNT(*) > 1
  )
  SELECT p2.id AS old_id, dg.keep_id
  FROM dup_groups dg
  JOIN products p2 ON LOWER(p2.name) = dg.name_norm AND p2.id <> dg.keep_id
) r
WHERE p.product_id = r.old_id;

-- Remap price_reports
UPDATE price_reports pr
SET    product_id = r.keep_id
FROM (
  WITH dup_groups AS (
    SELECT LOWER(name) AS name_norm, MIN(id) AS keep_id
    FROM products GROUP BY LOWER(name) HAVING COUNT(*) > 1
  )
  SELECT p2.id AS old_id, dg.keep_id
  FROM dup_groups dg
  JOIN products p2 ON LOWER(p2.name) = dg.name_norm AND p2.id <> dg.keep_id
) r
WHERE pr.product_id = r.old_id;

-- Remap promotions (if table exists)
UPDATE promotions pm
SET    product_id = r.keep_id
FROM (
  WITH dup_groups AS (
    SELECT LOWER(name) AS name_norm, MIN(id) AS keep_id
    FROM products GROUP BY LOWER(name) HAVING COUNT(*) > 1
  )
  SELECT p2.id AS old_id, dg.keep_id
  FROM dup_groups dg
  JOIN products p2 ON LOWER(p2.name) = dg.name_norm AND p2.id <> dg.keep_id
) r
WHERE pm.product_id = r.old_id;

-- 3. Delete the now-orphaned duplicate product rows
DELETE FROM products p
WHERE EXISTS (
  SELECT 1 FROM products q
  WHERE LOWER(q.name) = LOWER(p.name) AND q.id < p.id
);

-- 4. Add a unique constraint so this can't happen again
CREATE UNIQUE INDEX IF NOT EXISTS uniq_products_name_lower ON products(LOWER(name));

-- 5. Verification
SELECT LOWER(name) AS name_norm, COUNT(*) AS dups
FROM products GROUP BY LOWER(name) HAVING COUNT(*) > 1;
-- ↑ should return zero rows

SELECT s.name, p.price, p.source
FROM prices p
JOIN stores s ON s.id = p.store_id
JOIN products pr ON pr.id = p.product_id
WHERE pr.name = 'Cukinia'
ORDER BY s.name;
-- ↑ should return exactly one row per store
