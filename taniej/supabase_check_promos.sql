-- Check what's in promotions table
SELECT pr.id, pr.promo_price, pr.promo_label, pr.valid_from, pr.valid_until,
       p.name AS product, s.name AS store
FROM promotions pr
JOIN products p ON p.id = pr.product_id
JOIN stores s ON s.id = pr.store_id
ORDER BY s.name, p.name;
