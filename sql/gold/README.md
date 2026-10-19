# sql/gold

Warehouse scripts for the gold layer. Run them in the Warehouse `maison_gold`, in this order.

| File | When | What it does |
|---|---|---|
| `00_schemas_and_roles.sql` | once | creates one schema per region, the `cross_region` schema and the roles |
| `01_load_from_lakehouse.sql` | after every `nb_30_gold_build` run | copies the gold tables from the Lakehouse into the Warehouse |
| `02_views_regional.sql` | once (re-run if a column changes) | the views each region is allowed to see |
| `03_views_cross_region.sql` | once (re-run if a column changes) | the combined views, limited to people whose every record consents |
| `04_security.sql` | once | gives each role access to its own schema only |
| `05_checks.sql` | after every load | every query must return two equal numbers (`got` = `expected`) |

The view logic is written in plain SQL and is tested in Spark against the real gold tables (see `tests/`). The T-SQL wrappers (`CREATE OR ALTER VIEW`, roles, `GRANT`) are not tested outside the Warehouse.
