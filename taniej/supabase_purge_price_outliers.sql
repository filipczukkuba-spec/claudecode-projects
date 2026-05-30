-- Cleanup: remove absurd prices in the `prices` table.
-- These are scraped or estimated rows where the value is wildly out of line
-- vs the other stores' prices for the same product.
--
-- Rule: a price is an outlier if it is >= 5× the median price of OTHER stores
--       for the same product, OR if it exceeds 500 zł.
--
-- Preview first, then NULL out the bad prices (we keep the row so the
-- store/product pair still exists, just without a value).

-- 1. PREVIEW — see what will be wiped.
WITH median_per_product AS (
  SELECT
    p1.product_id,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p1.price) AS median_price
  FROM prices p1
  WHERE p1.price IS NOT NULL
  GROUP BY p1.product_id
)
SELECT
  pr.id,
  pr.product_id,
  prod.name        AS product,
  pr.store_id,
  s.name           AS store,
  pr.price,
  m.median_price,
  ROUND((pr.price / NULLIF(m.median_price, 0))::numeric, 1) AS multiplier,
  pr.source,
  CASE
    WHEN pr.price > 500 THEN 'over_500_zl'
    WHEN pr.price >= m.median_price * 5 THEN 'over_5x_median'
    ELSE 'ok'
  END AS reason
FROM prices pr
JOIN median_per_product m ON m.product_id = pr.product_id
LEFT JOIN products prod  ON prod.id      = pr.product_id
LEFT JOIN stores   s     ON s.id         = pr.store_id
WHERE pr.price IS NOT NULL
  AND (
        pr.price > 500
     OR pr.price >= m.median_price * 5
      )
ORDER BY multiplier DESC NULLS LAST;

-- 2. NULL out the bad scraped/estimated prices.
--    We don't DELETE because the row mapping product↔store is still useful.
WITH median_per_product AS (
  SELECT
    product_id,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS median_price
  FROM prices
  WHERE price IS NOT NULL
  GROUP BY product_id
)
UPDATE prices pr
SET    price       = NULL,
       source      = 'estimated',
       scraped_at  = NULL
FROM   median_per_product m
WHERE  m.product_id = pr.product_id
  AND  pr.price IS NOT NULL
  AND  (
         pr.price > 500
      OR pr.price >= m.median_price * 5
       );

-- 3. Verification.
SELECT COUNT(*) AS prices_over_500   FROM prices WHERE price > 500;
SELECT MAX(price) AS max_price       FROM prices;
