-- 03_views_cross_region.sql
-- The combined view across regions. Every view here lists ONLY people whose every record consents to sharing.
-- People without full consent do not appear at all.

EXEC('CREATE OR ALTER VIEW cross_region.v_person_360 AS
SELECT * FROM dbo.person_360_global');

EXEC('CREATE OR ALTER VIEW cross_region.v_client_identity_map AS
SELECT client_id, person_key, region, cluster_size, link_rule, link_confidence, is_anchor
FROM dbo.client_identity_map
WHERE consent_share_effective = 1');

EXEC('CREATE OR ALTER VIEW cross_region.v_sales AS
SELECT f.sale_id,
       f.date_key,
       f.event_date,
       f.client_id,
       f.person_key AS person_key,
       f.region,
       f.channel,
       f.boutique_id,
       f.sales_associate_id,
       f.product_id,
       f.category,
       f.quantity,
       f.currency,
       f.unit_price_eur,
       f.line_amount_eur,
       f.is_return,
       f.original_sale_id,
       f.days_to_return,
       f.fx_carried_forward
FROM dbo.fact_sales f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE d.consent_share_effective = 1');

EXEC('CREATE OR ALTER VIEW cross_region.v_after_sales AS
SELECT f.ticket_id,
       f.created_date_key,
       f.created_date,
       f.closed_date,
       f.client_id,
       f.person_key AS person_key,
       f.region,
       f.boutique_id,
       f.product_id,
       f.status,
       f.reason,
       f.purchase_region,
       f.service_region,
       f.is_cross_region_service,
       f.days_to_close
FROM dbo.fact_after_sales f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE d.consent_share_effective = 1');

EXEC('CREATE OR ALTER VIEW cross_region.v_appointments AS
SELECT f.appointment_id,
       f.date_key,
       f.appointment_date,
       f.client_id,
       f.person_key AS person_key,
       f.region,
       f.boutique_id,
       f.advisor_id,
       f.status
FROM dbo.fact_appointment f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE d.consent_share_effective = 1');

EXEC('CREATE OR ALTER VIEW cross_region.v_governance_summary AS
SELECT metric, value, as_of_date FROM dbo.governance_summary');

EXEC('CREATE OR ALTER VIEW cross_region.v_dim_boutique AS
SELECT boutique_id, city, country, region, currency FROM dbo.dim_boutique');

EXEC('CREATE OR ALTER VIEW cross_region.v_dim_product AS
SELECT product_id, name, category, sub_category, list_price_eur FROM dbo.dim_product');

EXEC('CREATE OR ALTER VIEW cross_region.v_dim_date AS
SELECT date_key, date, year, quarter, month, month_name, week_of_year, weekday, is_weekend FROM dbo.dim_date');
