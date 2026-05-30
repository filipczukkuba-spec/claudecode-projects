-- Fill ALL missing product×store combinations with estimated prices
-- Simpler than fill_gaps.sql — no PL/pgSQL variables, pure SQL
-- ON CONFLICT DO NOTHING = never overwrites scraped prices

WITH store_ratios AS (
  SELECT id, name,
    CASE name
      WHEN 'Aldi'      THEN 0.920
      WHEN 'Lidl'      THEN 0.940
      WHEN 'Netto'     THEN 0.970
      WHEN 'Biedronka' THEN 1.000
      WHEN 'Kaufland'  THEN 1.060
      WHEN 'Auchan'    THEN 1.090
      WHEN 'Carrefour' THEN 1.130
      ELSE 1.000
    END AS ratio
  FROM stores
),
best_base AS (
  -- Normalise whichever price exists to a "Biedronka equivalent"
  SELECT
    p.id AS product_id,
    COALESCE(
      MIN(CASE WHEN sr.name = 'Aldi'      THEN pr.price / 0.920 END),
      MIN(CASE WHEN sr.name = 'Biedronka' THEN pr.price          END),
      MIN(CASE WHEN sr.name = 'Lidl'      THEN pr.price / 0.940 END),
      MIN(CASE WHEN sr.name = 'Netto'     THEN pr.price / 0.970 END),
      MIN(CASE WHEN sr.name = 'Kaufland'  THEN pr.price / 1.060 END),
      MIN(CASE WHEN sr.name = 'Auchan'    THEN pr.price / 1.090 END),
      MIN(CASE WHEN sr.name = 'Carrefour' THEN pr.price / 1.130 END),
      MIN(pr.price),
      4.99
    ) AS base_price
  FROM products p
  LEFT JOIN prices pr ON pr.product_id = p.id
  LEFT JOIN store_ratios sr ON sr.id = pr.store_id
  GROUP BY p.id
)
INSERT INTO prices (product_id, store_id, price, source)
SELECT
  bb.product_id,
  sr.id,
  ROUND(CAST(bb.base_price * sr.ratio AS NUMERIC), 2),
  'estimated'
FROM best_base bb
CROSS JOIN store_ratios sr
WHERE NOT EXISTS (
  SELECT 1 FROM prices
  WHERE product_id = bb.product_id AND store_id = sr.id
)
ON CONFLICT (product_id, store_id) DO NOTHING;

-- Result: still_missing should be 0 for all stores
SELECT
  s.name,
  COUNT(*)                                   AS prices,
  (SELECT COUNT(*) FROM products) - COUNT(*) AS still_missing
FROM prices pr
JOIN stores s ON s.id = pr.store_id
GROUP BY s.name
ORDER BY s.name;
