-- One-off recalibration: bring 'estimated' prices in line with
-- 'scraped' and 'community' anchors for the same product.
--
-- Logic per product:
--   1. Compute the "Biedronka baseline" using any real anchor (scraped or
--      community) divided by that store's multiplier.
--   2. If multiple anchors exist, take the median of their baselines.
--   3. For every store where source='estimated', recompute price = baseline * store_multiplier.
--   4. Only update if the existing estimate differs by >50% (avoid churn).
--
-- Safe to re-run. Never overwrites 'scraped' or 'community' rows.

WITH multipliers(store_name, factor) AS (
  VALUES
    ('Biedronka', 1.00::numeric),
    ('Lidl',      0.97),
    ('Aldi',      0.98),
    ('Kaufland',  1.05),
    ('Netto',     0.99),
    ('Auchan',    1.06),
    ('Carrefour', 1.08)
),
-- All real anchors with their implied Biedronka-baseline
anchors AS (
  SELECT
    p.product_id,
    p.price / m.factor AS baseline
  FROM prices p
  JOIN stores s     ON s.id   = p.store_id
  JOIN multipliers m ON m.store_name = s.name
  WHERE p.price IS NOT NULL
    AND p.source IN ('scraped', 'community')
),
-- Median baseline per product (robust against outliers if multiple anchors disagree)
baseline_per_product AS (
  SELECT
    product_id,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY baseline) AS baseline
  FROM anchors
  GROUP BY product_id
),
-- Compute target estimated price per (product, store)
targets AS (
  SELECT
    bp.product_id,
    s.id        AS store_id,
    s.name      AS store_name,
    ROUND((bp.baseline * m.factor)::numeric, 2) AS target_price
  FROM baseline_per_product bp
  CROSS JOIN stores s
  JOIN multipliers m ON m.store_name = s.name
)
-- Update only 'estimated' rows that are off by >50%
UPDATE prices px
SET    price = t.target_price
FROM   targets t
WHERE  t.product_id = px.product_id
  AND  t.store_id   = px.store_id
  AND  px.source    = 'estimated'
  AND  t.target_price > 0
  AND  (
         px.price IS NULL
      OR ABS(px.price - t.target_price) / t.target_price > 0.50
       );

-- Verification: rows updated, plus a sanity check for Cukinia in particular
SELECT 'Cukinia after recalibration' AS label, s.name, p.price, p.source
FROM prices p
JOIN stores s ON s.id = p.store_id
JOIN products pr ON pr.id = p.product_id
WHERE pr.name = 'Cukinia'
ORDER BY s.name;
