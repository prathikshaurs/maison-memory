# Runbook: Maison Memory daily pipeline

Maison Cambon is fictional and all data is synthetic. This runbook describes how the project's own pipeline behaves.

## What runs

Pipeline `pl_maison_daily` runs the driver notebook `nb_90_run_pipeline`, then loads the Warehouse with a SQL script, and sends an email alert if a step fails.

The driver runs these notebooks in order. Each has a 1 hour limit.

| Order | Notebook | Does |
|---|---|---|
| 1 | nb_10_bronze_ingest | Loads new landing files to bronze, logs every file |
| 2 | nb_20_silver_clean | Cleans CRM clients, applies reject rules, writes quarantine |
| 3 | nb_21_silver_sales | Builds sales and after-sales, converts currency, reconciles |
| 4 | nb_21b_silver_history_retention | Client history, retention, erasure |
| 5 | nb_22_silver_identity | Matches clients across regions |
| 6 | nb_30_gold_build | Gold tables and 10 reconciliation checks |

Every step writes a row to `ctl_pipeline_run`. Row `_pipeline` (step order 0) holds the overall result.

## When a run fails

1. Open `ctl_pipeline_run` for the run id in the alert email. Find the row with `status = failed`.
2. Read `failure_class`, `retryable` and `suggested_action`. Steps after the failure are recorded as `skipped`.
3. Act by class:

| Class | Meaning | First action | Retry? |
|---|---|---|---|
| source | A file is missing, short or corrupt | Check `ctl_file_log` for the batch. Ask the source team for a corrected file | No, not until the input changes |
| integration | A table, column or type does not match what the step expects | Check that earlier steps finished and that no schema changed | No |
| processing | One of our own checks failed (reconciliation, integrity) | Read the check output of the failed notebook before changing anything | No |
| infrastructure | The platform failed (timeout, throttling, session lost) | Retry once. If it repeats, check capacity | Yes, once |
| unknown | No rule matched | Read the full error, classify by hand, add a rule to `CLASS_RULES` in nb_90 and a test | No |

4. After the fix, rerun the pipeline. Loads are idempotent, so a rerun does not duplicate data.

## Failure drill

To test alerting without breaking anything, set the pipeline parameter `SIMULATE_FAILURE` to `step_name|error text`, for example `nb_21_silver_sales|Cannot cast column amount: datatype mismatch`. The named step is not run, it fails with that text, and its rows are marked `is_simulated = 1`. The Power BI Pipeline Health page can filter these out.

## Refreshing the Power BI model

`dbo.pipeline_run` and `dbo.dq_results` in the Warehouse are copies of the Lakehouse control tables. After a run, execute `sql/gold/06_ops_tables.sql` in the Warehouse to refresh them. This is manual in this project.

## Erasure and retention

- Prospects expire after a regional number of months without activity (set in nb_21b). Relationship clients are held for review, never deleted by the job.
- Erased clients are recorded as hashed ids in `ctl_erasure_tombstone`. nb_20 rejects them if a source sends them again.
- Delta keeps old file versions until `VACUUM`. Removing a record from a table does not remove it from older versions. A real deployment needs a vacuum schedule and a documented retention period for time travel. This project documents the gap and does not run VACUUM.

## Known limits

- Region role security (`role_<region>`, `role_cross_region`) is defined in `sql/gold/04_security.sql` but was not tested with separate users, because the trial has a single user.
- T-SQL view wrappers were verified by round trip in the Warehouse. The view logic itself was tested in Spark.
- The Power BI model reads the base Warehouse tables, so it shows aggregates only and hides identifier columns. It does not apply the per-region roles.
