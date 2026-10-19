-- 02_views_regional.sql
-- One set of views per region. They are the ONLY thing a regional role can read.
-- A client's person_key is shown only when every record of that person consents to sharing across regions.
-- Each view is wrapped in EXEC(...) so the whole file can run in one go.

EXEC('CREATE OR ALTER VIEW rg_americas.v_client_360 AS
SELECT c.client_id,
       c.region,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       d.home_boutique_id,
       d.home_country,
       d.created_date,
       d.consent_share_cross_region,
       d.consent_marketing,
       d.consent_share_effective,
       d.source_segment,
       c.orders,
       c.return_lines,
       c.net_sales_eur,
       c.gross_sales_eur,
       c.returned_eur,
       c.net_sales_12m_eur,
       c.first_purchase_date,
       c.last_purchase_date,
       c.days_since_last_purchase,
       c.boutique_share,
       c.top_category,
       c.repairs,
       c.open_repairs,
       c.cross_region_repairs,
       c.appointments,
       c.completed_appointments,
       c.no_shows,
       c.tier,
       c.as_of_date
FROM dbo.client_360 c
JOIN dbo.dim_client d ON d.client_id = c.client_id
WHERE c.region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_client_names AS
SELECT client_id, first_name, last_name
FROM dbo.dim_client
WHERE region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_sales AS
SELECT f.sale_id,
       f.date_key,
       f.event_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_after_sales AS
SELECT f.ticket_id,
       f.created_date_key,
       f.created_date,
       f.closed_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_appointments AS
SELECT f.appointment_id,
       f.date_key,
       f.appointment_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       f.region,
       f.boutique_id,
       f.advisor_id,
       f.status
FROM dbo.fact_appointment f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE f.region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_dim_boutique AS
SELECT boutique_id, city, country, region, currency
FROM dbo.dim_boutique
WHERE region = ''americas''');

EXEC('CREATE OR ALTER VIEW rg_americas.v_dim_product AS
SELECT product_id, name, category, sub_category, list_price_eur
FROM dbo.dim_product');

EXEC('CREATE OR ALTER VIEW rg_americas.v_dim_date AS
SELECT date_key, date, year, quarter, month, month_name, week_of_year, weekday, is_weekend
FROM dbo.dim_date');

EXEC('CREATE OR ALTER VIEW rg_europe.v_client_360 AS
SELECT c.client_id,
       c.region,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       d.home_boutique_id,
       d.home_country,
       d.created_date,
       d.consent_share_cross_region,
       d.consent_marketing,
       d.consent_share_effective,
       d.source_segment,
       c.orders,
       c.return_lines,
       c.net_sales_eur,
       c.gross_sales_eur,
       c.returned_eur,
       c.net_sales_12m_eur,
       c.first_purchase_date,
       c.last_purchase_date,
       c.days_since_last_purchase,
       c.boutique_share,
       c.top_category,
       c.repairs,
       c.open_repairs,
       c.cross_region_repairs,
       c.appointments,
       c.completed_appointments,
       c.no_shows,
       c.tier,
       c.as_of_date
FROM dbo.client_360 c
JOIN dbo.dim_client d ON d.client_id = c.client_id
WHERE c.region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_client_names AS
SELECT client_id, first_name, last_name
FROM dbo.dim_client
WHERE region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_sales AS
SELECT f.sale_id,
       f.date_key,
       f.event_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_after_sales AS
SELECT f.ticket_id,
       f.created_date_key,
       f.created_date,
       f.closed_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_appointments AS
SELECT f.appointment_id,
       f.date_key,
       f.appointment_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       f.region,
       f.boutique_id,
       f.advisor_id,
       f.status
FROM dbo.fact_appointment f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE f.region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_dim_boutique AS
SELECT boutique_id, city, country, region, currency
FROM dbo.dim_boutique
WHERE region = ''europe''');

EXEC('CREATE OR ALTER VIEW rg_europe.v_dim_product AS
SELECT product_id, name, category, sub_category, list_price_eur
FROM dbo.dim_product');

EXEC('CREATE OR ALTER VIEW rg_europe.v_dim_date AS
SELECT date_key, date, year, quarter, month, month_name, week_of_year, weekday, is_weekend
FROM dbo.dim_date');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_client_360 AS
SELECT c.client_id,
       c.region,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       d.home_boutique_id,
       d.home_country,
       d.created_date,
       d.consent_share_cross_region,
       d.consent_marketing,
       d.consent_share_effective,
       d.source_segment,
       c.orders,
       c.return_lines,
       c.net_sales_eur,
       c.gross_sales_eur,
       c.returned_eur,
       c.net_sales_12m_eur,
       c.first_purchase_date,
       c.last_purchase_date,
       c.days_since_last_purchase,
       c.boutique_share,
       c.top_category,
       c.repairs,
       c.open_repairs,
       c.cross_region_repairs,
       c.appointments,
       c.completed_appointments,
       c.no_shows,
       c.tier,
       c.as_of_date
FROM dbo.client_360 c
JOIN dbo.dim_client d ON d.client_id = c.client_id
WHERE c.region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_client_names AS
SELECT client_id, first_name, last_name
FROM dbo.dim_client
WHERE region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_sales AS
SELECT f.sale_id,
       f.date_key,
       f.event_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_after_sales AS
SELECT f.ticket_id,
       f.created_date_key,
       f.created_date,
       f.closed_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
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
WHERE f.region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_appointments AS
SELECT f.appointment_id,
       f.date_key,
       f.appointment_date,
       f.client_id,
       CASE WHEN d.consent_share_effective = 1 THEN d.person_key END AS person_key,
       f.region,
       f.boutique_id,
       f.advisor_id,
       f.status
FROM dbo.fact_appointment f
JOIN dbo.dim_client d ON d.client_id = f.client_id
WHERE f.region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_dim_boutique AS
SELECT boutique_id, city, country, region, currency
FROM dbo.dim_boutique
WHERE region = ''asia_pacific''');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_dim_product AS
SELECT product_id, name, category, sub_category, list_price_eur
FROM dbo.dim_product');

EXEC('CREATE OR ALTER VIEW rg_asia_pacific.v_dim_date AS
SELECT date_key, date, year, quarter, month, month_name, week_of_year, weekday, is_weekend
FROM dbo.dim_date');
