# Source to target mapping

Table level view of how data moves through the layers. Column level rules are in the notebooks and in `docs/architecture/design.md`.

## Sources (per region unless stated)

| Source file | Bronze | Silver | Gold |
|---|---|---|---|
| crm_client | bronze_crm_client | silver_crm_client (all versions) | gold_dim_client, gold_client_360 |
| pos_transaction | bronze_pos_transaction | silver_sales (with ecom) | gold_fact_sales |
| ecom_order | bronze_ecom_order | silver_sales | gold_fact_sales |
| after_sales_ticket | bronze_after_sales_ticket | silver_after_sales | gold_fact_after_sales |
| appointment | bronze_appointment | silver_appointment | gold_fact_appointment |
| product (reference) | bronze_product | silver_product | gold_dim_product |
| boutique (reference) | bronze_boutique | silver_boutique | gold_dim_boutique |
| fx_rate (reference) | bronze_fx_rate | silver_fx_rate_daily | used to convert amounts to EUR |
| _manifest | bronze_manifest | not used | used to check late and short files |

## Derived tables

| Table | Built by | From | Purpose |
|---|---|---|---|
| silver_client_history | nb_21b | silver_crm_client | Slowly changing history (valid_from, valid_to, is_current, changed_columns) |
| silver_client_identity | nb_22 | silver_crm_client | Which client records are the same person, with rule and confidence |
| gold_client_identity_map | nb_30 | silver identity | Client to person_key link, with rule and confidence |
| gold_client_360 | nb_30 | gold dims and facts | One row per client record: sales, repairs, appointments, tier |
| gold_person_360_global | nb_30 | gold_client_360 | One row per person, only people whose every record consents to sharing |
| gold_governance_summary | nb_30 | gold tables | Counts used for governance reporting |

## Control tables (Lakehouse)

| Table | Written by | Purpose |
|---|---|---|
| ctl_file_log | nb_10 | Every landing file and its load result |
| ctl_run_log | notebooks | Per object load status and row counts |
| ctl_dq_results | notebooks | One row per data quality rule per batch |
| ctl_quarantine | nb_20, nb_21 | Rejected rows, rule broken, failure class (raw record redacted for erased clients) |
| ctl_retention_rules, ctl_retention_log | nb_21b | Retention limits and what was purged or held |
| ctl_erasure_tombstone | nb_21b | Hashed ids of erased clients |
| ctl_identity_eval | nb_29 | Match accuracy against ground truth |
| ctl_pipeline_run | nb_90 | Result and failure class for every pipeline step |

## Warehouse (maison_gold)

`sql/gold/01_load_from_lakehouse.sql` copies the gold tables into `dbo`. Views are created per region in schemas `rg_americas`, `rg_europe`, `rg_asia_pacific` and in `cross_region`. `sql/gold/06_ops_tables.sql` copies `ctl_pipeline_run` and `ctl_dq_results` as `dbo.pipeline_run` and `dbo.dq_results` for the report.
