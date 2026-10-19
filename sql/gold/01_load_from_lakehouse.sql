-- 01_load_from_lakehouse.sql
-- Copies the gold tables built by nb_30_gold_build from the Lakehouse into the Warehouse.
-- Needs the Lakehouse 'lh_maison' added to this Warehouse in the Explorer (+ Warehouses / Lakehouses).
-- Run again after every nb_30 run. The views in 02 and 03 stay in place.

DROP TABLE IF EXISTS dbo.dim_client;
CREATE TABLE dbo.dim_client AS
SELECT * FROM lh_maison.dbo.gold_dim_client;

DROP TABLE IF EXISTS dbo.dim_product;
CREATE TABLE dbo.dim_product AS
SELECT * FROM lh_maison.dbo.gold_dim_product;

DROP TABLE IF EXISTS dbo.dim_boutique;
CREATE TABLE dbo.dim_boutique AS
SELECT * FROM lh_maison.dbo.gold_dim_boutique;

DROP TABLE IF EXISTS dbo.dim_date;
CREATE TABLE dbo.dim_date AS
SELECT * FROM lh_maison.dbo.gold_dim_date;

DROP TABLE IF EXISTS dbo.fact_sales;
CREATE TABLE dbo.fact_sales AS
SELECT * FROM lh_maison.dbo.gold_fact_sales;

DROP TABLE IF EXISTS dbo.fact_after_sales;
CREATE TABLE dbo.fact_after_sales AS
SELECT * FROM lh_maison.dbo.gold_fact_after_sales;

DROP TABLE IF EXISTS dbo.fact_appointment;
CREATE TABLE dbo.fact_appointment AS
SELECT * FROM lh_maison.dbo.gold_fact_appointment;

DROP TABLE IF EXISTS dbo.client_identity_map;
CREATE TABLE dbo.client_identity_map AS
SELECT * FROM lh_maison.dbo.gold_client_identity_map;

DROP TABLE IF EXISTS dbo.client_360;
CREATE TABLE dbo.client_360 AS
SELECT * FROM lh_maison.dbo.gold_client_360;

DROP TABLE IF EXISTS dbo.person_360_global;
CREATE TABLE dbo.person_360_global AS
SELECT * FROM lh_maison.dbo.gold_person_360_global;

DROP TABLE IF EXISTS dbo.governance_summary;
CREATE TABLE dbo.governance_summary AS
SELECT * FROM lh_maison.dbo.gold_governance_summary;
