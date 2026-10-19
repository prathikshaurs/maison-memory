-- 00_schemas_and_roles.sql
-- Run once in the Warehouse (maison_gold). Safe to run again: it only creates what is missing.
-- One schema per region, one for the consent-gated cross-region views. Base tables stay in dbo and nobody gets access to dbo.
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'rg_americas') EXEC('CREATE SCHEMA rg_americas');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'rg_europe') EXEC('CREATE SCHEMA rg_europe');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'rg_asia_pacific') EXEC('CREATE SCHEMA rg_asia_pacific');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'cross_region') EXEC('CREATE SCHEMA cross_region');

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_americas') CREATE ROLE role_americas;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_europe') CREATE ROLE role_europe;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_asia_pacific') CREATE ROLE role_asia_pacific;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'role_cross_region') CREATE ROLE role_cross_region;
