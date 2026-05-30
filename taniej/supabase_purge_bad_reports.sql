-- Cleanup: remove user-submitted price reports that are clearly absurd.
-- Run ONCE in Supabase SQL Editor.
--
-- Rules (mirroring server-side validation in /api/report-price):
--  1) Drop any report > 500 zł (no grocery item costs more).
--  2) Drop any report > 3× the trusted reference price for the same
--     product+store, where reference = MIN(price, app_price).
--
-- Preview first, then DELETE.

-- 1. Preview what will be deleted (run this first to inspect).
SELECT
  pr.id,
  pr.product_id,
  p.name        AS product,
  pr.store_id,
  s.name        AS store,
  pr.price      AS reported,
  pr.city,
  pr.submitted_at,
  LEAST(NULLIF(px.price, 0), NULLIF(px.app_price, 0)) AS reference_price,
  CASE
    WHEN pr.price > 500 THEN 'over_500_zl'
    WHEN pr.price > LEAST(NULLIF(px.price, 0), NULLIF(px.app_price, 0)) * 3 THEN 'over_3x_reference'
    ELSE 'ok'
  END AS reason
FROM price_reports pr
LEFT JOIN prices   px ON px.product_id = pr.product_id AND px.store_id = pr.store_id
LEFT JOIN products p  ON p.id          = pr.product_id
LEFT JOIN stores   s  ON s.id          = pr.store_id
WHERE pr.price > 500
   OR pr.price > LEAST(NULLIF(px.price, 0), NULLIF(px.app_price, 0)) * 3
ORDER BY pr.price DESC;

-- 2. Once you've reviewed the list above, run the DELETE:
DELETE FROM price_reports pr
USING prices px
WHERE px.product_id = pr.product_id
  AND px.store_id   = pr.store_id
  AND (
        pr.price > 500
     OR pr.price > LEAST(NULLIF(px.price, 0), NULLIF(px.app_price, 0)) * 3
      );

-- Also drop reports with no reference at all and price > 500 (covers products
-- with no scraped/estimated row).
DELETE FROM price_reports WHERE price > 500;

-- 3. Verification.
SELECT COUNT(*) AS remaining_reports FROM price_reports;
SELECT MAX(price) AS max_remaining_price FROM price_reports;
