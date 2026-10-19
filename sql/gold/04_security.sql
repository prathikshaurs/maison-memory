-- 04_security.sql
-- Roles only get SELECT on their own view schema. Nobody is granted anything on dbo (the base tables).

GRANT SELECT ON SCHEMA::rg_americas TO role_americas;
GRANT SELECT ON SCHEMA::rg_europe TO role_europe;
GRANT SELECT ON SCHEMA::rg_asia_pacific TO role_asia_pacific;
GRANT SELECT ON SCHEMA::cross_region TO role_cross_region;

-- Add people to a role like this (replace the name):
-- ALTER ROLE role_americas ADD MEMBER [name@yourtenant.edu];
-- ALTER ROLE role_europe ADD MEMBER [name@yourtenant.edu];
-- ALTER ROLE role_asia_pacific ADD MEMBER [name@yourtenant.edu];
-- ALTER ROLE role_cross_region ADD MEMBER [name@yourtenant.edu];
