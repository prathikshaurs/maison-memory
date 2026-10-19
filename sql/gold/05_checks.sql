-- 05_checks.sql
-- Every query returns two numbers: got and expected. They must be equal.

-- regional sales views add up to the base table
SELECT (SELECT COUNT(*) FROM rg_americas.v_sales) + (SELECT COUNT(*) FROM rg_europe.v_sales) + (SELECT COUNT(*) FROM rg_asia_pacific.v_sales) AS got, (SELECT COUNT(*) FROM dbo.fact_sales) AS expected;

-- regional client views add up to dim_client
SELECT (SELECT COUNT(*) FROM rg_americas.v_client_360) + (SELECT COUNT(*) FROM rg_europe.v_client_360) + (SELECT COUNT(*) FROM rg_asia_pacific.v_client_360) AS got, (SELECT COUNT(*) FROM dbo.dim_client) AS expected;

-- regional repair views add up to the base table
SELECT (SELECT COUNT(*) FROM rg_americas.v_after_sales) + (SELECT COUNT(*) FROM rg_europe.v_after_sales) + (SELECT COUNT(*) FROM rg_asia_pacific.v_after_sales) AS got, (SELECT COUNT(*) FROM dbo.fact_after_sales) AS expected;

-- a region view shows only its own region
SELECT (SELECT COUNT(*) FROM rg_europe.v_sales WHERE region <> 'europe') + (SELECT COUNT(*) FROM rg_americas.v_client_360 WHERE region <> 'americas') + (SELECT COUNT(*) FROM rg_asia_pacific.v_after_sales WHERE region <> 'asia_pacific') AS got, 0 AS expected;

-- regional views never show a person key without full consent
SELECT (SELECT COUNT(*) FROM rg_americas.v_client_360 WHERE person_key IS NOT NULL AND consent_share_effective = 0) + (SELECT COUNT(*) FROM rg_europe.v_client_360 WHERE person_key IS NOT NULL AND consent_share_effective = 0) + (SELECT COUNT(*) FROM rg_asia_pacific.v_client_360 WHERE person_key IS NOT NULL AND consent_share_effective = 0) AS got, 0 AS expected;

-- regional sales views never show a person key without full consent
SELECT COUNT(*) AS got, 0 AS expected FROM rg_europe.v_sales s JOIN dbo.dim_client d ON d.client_id = s.client_id WHERE s.person_key IS NOT NULL AND d.consent_share_effective = 0;

-- the cross-region sales view contains only consenting people
SELECT COUNT(*) AS got, 0 AS expected FROM cross_region.v_sales s JOIN dbo.dim_client d ON d.client_id = s.client_id WHERE d.consent_share_effective = 0;

-- the cross-region identity map contains only consenting people
SELECT COUNT(*) AS got, 0 AS expected FROM cross_region.v_client_identity_map m JOIN dbo.dim_client d ON d.client_id = m.client_id WHERE d.consent_share_effective = 0;

-- the person profile has no person without full consent
SELECT COUNT(*) AS got, 0 AS expected FROM cross_region.v_person_360 p JOIN dbo.dim_client d ON d.person_key = p.person_key WHERE d.consent_share_effective = 0;
