# Synthetic data generator

Creates the source data for Maison Memory. **Maison Cambon is a fictional luxury house and every row is made up.** Nothing here is real client data or data from any real company.

```bash
python data_generator/generate_data.py            # default: 5,000 people, 12 months, seed 42
python data_generator/generate_data.py --people 1000 --seed 7
pytest -q                                          # checks the planted problems and repeatability
```

The same seed always gives the same files, so results are reproducible. The script deletes and rebuilds `data/raw` and `data/truth` on every run.

## What it produces

```
data/raw/<region>/dt=YYYY-MM-DD/<table>.csv   daily files, one folder per region and day
data/raw/reference/                           product.csv, boutique.csv, fx_rate.csv
data/raw/_manifest.csv                        promised row count and arrival time of every file
data/truth/person_truth.csv                   which records belong to the same real person
data/truth/summary.json                       counts of every planted problem
```

`data/truth` is the answer key. It is used by tests to measure the identity matching. It is never loaded into Fabric.

Default size: about 5,000 people (5,273 CRM records), about 100,000 sales rows plus about 3,800 returns, about 1,500 repairs, about 4,300 appointments, about 4,900 files.

## Tables

| Table | Sent by | Notes |
|---|---|---|
| `crm_client` | each region | First day holds the existing base, later days hold new clients and changes |
| `pos_transaction` | each region | One product per row, boutique sales |
| `ecom_order` | each region | One product per row, online orders |
| `after_sales_ticket` | each region | Repairs and services, status changes by age |
| `appointment` | each region | Mostly VIC and high spenders |
| `product`, `boutique`, `fx_rate` | reference | `fx_rate` has weekdays only |

Timestamps are local time of the region, with no time zone. Prices are local price lists in each boutique's currency (USD, CAD, EUR, GBP, CHF, KRW, JPY, HKD).

## Planted problems (default run)

| Problem | What the pipeline must do | Count |
|---|---|---|
| Same person in two regions, with a spelling variation | Match them and record the rule used | 273 people |
| Missing consent values | Treat as no consent | 404 |
| Regions disagree about consent | Apply the most restrictive value | 64 |
| Consent changes during the year | Keep history | 164 |
| Messy emails and names (case, trailing spaces) | Clean before matching | 229 and 110 |
| Transactions for clients that do not exist | Quarantine | 292 |
| Missing price | Quarantine | 172 |
| Product not in the catalog | Quarantine | 211 |
| Row dated in the future | Quarantine | 108 |
| Same row sent again the next day | Remove duplicates | 371 |
| Batch arrives late (1 or 3 days) | Flag freshness breach | 31 |
| File has fewer rows than the manifest promises | Reconciliation failure | 5 |
| Europe `crm_client` gains `client_segment` in week 3 | Absorb the new column | from day 21 |
| Americas `pos_transaction` gains `sales_associate_id` | Absorb the new column | from day 120 |
| Returns as negative quantities | Handle in net sales | about 3,800 |
| Mixed currencies, no weekend FX rates | Convert with the last known rate | all |

Counts are exact for seed 42 and can shift slightly with a different seed.

## Design choices

- **Purchases stay in the region where they happen.** Only people registered in two regions have activity in both, which mirrors the idea that a client is a separate record in each region until the data product links them.
- **Prospects** are people with no purchases. About 40 percent of them were created more than three years before the start date so the retention job has something to remove.
- **Names** are romanized so fuzzy matching is a fair test, not a script problem.
- **CSV, not Parquet.** Source systems usually send CSV, and it makes schema changes and bad rows easy to inspect.
