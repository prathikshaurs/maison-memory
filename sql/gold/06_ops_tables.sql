-- 06_ops_tables.sql
-- Copies the pipeline run log and data quality results into the Warehouse so one report can read everything.
DROP TABLE IF EXISTS dbo.pipeline_run;
CREATE TABLE dbo.pipeline_run AS
SELECT * FROM lh_maison.dbo.ctl_pipeline_run;

DROP TABLE IF EXISTS dbo.dq_results;
CREATE TABLE dbo.dq_results AS
SELECT * FROM lh_maison.dbo.ctl_dq_results;

SELECT 'pipeline_run' AS tbl, COUNT(*) AS row_count FROM dbo.pipeline_run
UNION ALL
SELECT 'dq_results', COUNT(*) FROM dbo.dq_results;