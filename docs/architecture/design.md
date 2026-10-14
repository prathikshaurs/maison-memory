# Maison Memory: Design

![Architecture](architecture.png)

> Maison Cambon is a fictional luxury house. All data in this project is synthetic. This design is modeled on publicly available information about enterprise data platforms and is not affiliated with any real brand.

## 1. Purpose

A luxury house wants a client to be recognized wherever she shops: a boutique in New York, a repair in Seoul, an online order from Paris. The hard part is not drawing a single client view. It is keeping that view **accurate, consent-aware, auditable and operable by a team** when each region runs its own systems under its own rules.

This project builds that data product on Microsoft Fabric, end to end, from raw regional files to a Power BI report, with the controls an enterprise data team would expect.

## 2. Scenario

Maison Cambon operates in three regions, each with its own source systems:

| Region | Example city | Notes |
|---|---|---|
| Americas | New York | Own CRM, POS and e-commerce |
| Europe | Paris | Own CRM, POS and e-commerce |
| Asia-Pacific | Seoul | Own CRM, POS and e-commerce |

Each region sends daily files. The data product combines them into one trusted client view and applies consent rules before anything crosses a region boundary.

## 3. Platform and tools

| Layer | Fabric tool |
|---|---|
| Orchestration | Data Factory pipeline |
| Landing | OneLake Files |
| Bronze and silver | Lakehouse, PySpark notebooks, Delta Lake |
| Gold | Warehouse (SQL) |
| Reporting | Power BI in the Fabric browser experience |
| Code safety | Git integration, deployment pipelines |
| Supporting | Python (data generation, tests), GitHub |

## 4. Layers

**Landing.** Raw files exactly as received, one folder per region and day. Late and missing files are expected.

**Bronze.** Raw data stored as Delta tables with no business changes. Every row is stamped with a batch ID and load time. New columns from a source are absorbed without breaking the load.

**Silver.** Typed and cleaned. Duplicates removed, currencies standardized, returns handled, and identity matching applied across regions. Invalid rows go to a quarantine table with the reason. Client history is kept over time.

**Gold.** Business-ready tables in the Warehouse. Consent-aware views control what each region may see.

**Consumption.** A Power BI report with two pages: Client Insights and Pipeline Health.

## 5. Data model

### Source tables (per region)

| Table | Key columns |
|---|---|
| `crm_client` | client_id, region, first_name, last_name, email, phone, home_boutique_id, created_at, updated_at, consent_share_cross_region, consent_marketing |
| `pos_transaction` | transaction_id, client_id, boutique_id, product_id, quantity, unit_price, currency, is_return, transaction_ts |
| `ecom_order` | order_id, client_id, product_id, quantity, unit_price, currency, is_return, order_ts |
| `after_sales_ticket` | ticket_id, client_id, boutique_id, product_id, status, reason, created_at, closed_at |
| `appointment` | appointment_id, client_id, boutique_id, advisor_id, appointment_ts |
| `product` | product_id, category (Fashion, Watches and Jewelry, Fragrance and Beauty), name, list_price_eur |
| `boutique` | boutique_id, city, region |
| `fx_rate` | currency, rate_date, rate_to_eur |

### Gold tables

| Table | Purpose |
|---|---|
| `dim_client` | One row per real person with a global client ID, home region and VIC tier. Uses valid_from and valid_to so tier changes are kept as history. |
| `client_identity_map` | Links each regional client record to the global ID. Stores the match rule used and a confidence score so every match can be audited. |
| `fact_sales` | Sales and returns in a common currency. |
| `fact_after_sales` | Repairs and service tickets. |
| `client_360` | One row per client: lifetime spend, categories bought, last visit, open repairs. |

### Control tables (Lakehouse)

| Table | Purpose |
|---|---|
| `ctl_run_log` | Batch ID, layer, status, start and end time, row counts in and out |
| `ctl_dq_results` | One row per data quality rule per batch: rule, rows checked, rows failed |
| `ctl_quarantine` | Rejected rows with source, rule broken and failure class |
| `ctl_watermark` | Where each incremental load stopped, so a restart resumes correctly |

## 6. Design decisions

1. **Restartable and idempotent.** Every load carries a batch ID and writes with MERGE, so running it twice never creates duplicates. A watermark table remembers where each load stopped.
2. **Schema evolution.** A region adds a new column partway through the data. Bronze absorbs it, silver maps it, and a test confirms nothing breaks.
3. **Identity matching.** First match on hashed email. Then fuzzy match on name plus phone for the rest. Every decision is recorded with the rule and a confidence score.
4. **Consent as a rule.** Cross-region visibility depends on the client's home region and consent flag (see section 7).
5. **Privacy by design.** Fake data only. Emails are hashed, and names are masked when viewed from a region that is not allowed to see them.
6. **Retention.** A scheduled job removes prospects after 3 years and clients 10 years after the end of the relationship, matching the retention periods described in a public luxury-house privacy policy.
7. **Failure classification.** Every failure is tagged as source, integration, processing, orchestration or consumption, so the right team is told.

## 7. Consent and visibility rules

This is a design assumption, not a claim about how any real company works.

| Viewer | Client consented to cross-region sharing | Client did not consent |
|---|---|---|
| Home region | Full profile | Full profile |
| Other region | Full profile | Masked: initials only, no contact details, spend shown as a band |

Gold views enforce this rule so no report can bypass it. The same client viewed from New York, Paris and Seoul will therefore look different depending on consent.

## 8. Deliberate data problems

Real data is messy, so the generator injects realistic problems and the pipeline must handle them:

- The same person registered in two regions with different spellings
- Files that arrive a day late
- A new column appearing in week 3
- Returns recorded as negative quantities
- Prices in different currencies
- Transactions that point to clients that do not exist
- Missing consent values

## 9. Testing and quality

- **Unit tests** for transformation functions (Python, pytest)
- **Data quality rules** run on every batch and written to `ctl_dq_results`
- **Reconciliation:** row counts and totals compared between layers and against the source
- **Regression tests** on the injected problems, so a fix cannot silently break
- **Deployment checks** before promotion from dev to test to prod

## 10. DataOps

- Git integration on the Fabric workspace, with pull requests for changes
- Deployment pipelines: dev to test to prod
- Environment configuration kept separate from code
- Runbook with failure classes, first checks and recovery steps (`docs/runbooks/`)
- Source-to-target mappings (`docs/mappings/`)

## 11. Scope and defaults

| Item | Value |
|---|---|
| Clients | about 5,000 |
| Transactions | about 100,000 over 12 months |
| Regions | 3 |
| Data | Fully synthetic |

## 12. Out of scope

- Real client or company data
- Any claim about the internal systems of a real company
- Semantic model and metric governance beyond a simple Power BI report
- Production-grade security hardening beyond the controls listed here

## 13. Status

- [x] Design and architecture
- [ ] Synthetic data generator
- [ ] Bronze layer
- [ ] Silver layer
- [ ] Gold layer
- [ ] Orchestration and control tables
- [ ] Tests and CI
- [ ] Power BI report
- [ ] Runbook and mappings
