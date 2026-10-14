"""Tests for the synthetic data generator.

They run the generator on a small dataset (600 people) and check that the data
has the shape the pipeline will rely on: the planted problems exist, the files
match the manifest, and two runs with the same seed give identical output.
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_generator"))
import generate_data as gd  # noqa: E402

REGIONS = gd.REGION_ORDER


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    folder = tmp_path_factory.mktemp("data")
    gd.generate(folder, n_people=600, seed=7, verbose=False)
    return folder


def read_all(out, table, region=None):
    frames = []
    for r in [region] if region else REGIONS:
        for f in sorted((out / "raw" / r).glob(f"dt=*/{table}.csv")):
            df = pd.read_csv(f, dtype=str)
            df["_dt"] = f.parent.name.replace("dt=", "")
            df["_region"] = r
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def test_manifest_matches_files(out):
    manifest = pd.read_csv(out / "raw" / "_manifest.csv")
    assert len(manifest) > 1000
    for path in manifest["file_path"].sample(50, random_state=1):
        assert (out / "raw" / path).exists()
    # Rows in a file never exceed what the manifest promised
    for _, m in manifest.sample(200, random_state=2).iterrows():
        actual = len(pd.read_csv(out / "raw" / m["file_path"], dtype=str))
        assert actual <= m["row_count"]


def test_some_files_are_short_or_late(out):
    manifest = pd.read_csv(out / "raw" / "_manifest.csv")
    short = 0
    for _, m in manifest.iterrows():
        if len(pd.read_csv(out / "raw" / m["file_path"], dtype=str)) < m["row_count"]:
            short += 1
    assert short >= 1
    lag = (pd.to_datetime(manifest["actual_arrival_ts"]) - pd.to_datetime(manifest["expected_arrival_ts"]))
    assert (lag > pd.Timedelta(hours=20)).any()


def test_europe_schema_change_in_week_3(out):
    crm = read_all(out, "crm_client", "europe")
    cutoff = (gd.DEFAULT_START + pd.Timedelta(days=gd.EUROPE_SCHEMA_CHANGE_DAY)).isoformat()
    before = crm[crm["_dt"] < cutoff]
    first_after = sorted((out / "raw" / "europe").glob("dt=*/crm_client.csv"))
    cols_before = pd.read_csv(sorted(first_after)[0], nrows=1).columns
    assert "client_segment" not in cols_before
    after_files = [f for f in first_after if f.parent.name.replace("dt=", "") >= cutoff]
    assert "client_segment" in pd.read_csv(after_files[0], nrows=1).columns
    assert len(before) > 0


def test_americas_pos_gains_sales_associate_later(out):
    files = sorted((out / "raw" / "americas").glob("dt=*/pos_transaction.csv"))
    assert "sales_associate_id" not in pd.read_csv(files[0], nrows=1).columns
    assert "sales_associate_id" in pd.read_csv(files[-1], nrows=1).columns


def test_returns_are_negative_quantities(out):
    pos = read_all(out, "pos_transaction")
    returns = pos[pos["is_return"] == "1"]
    assert len(returns) > 0
    assert (returns["quantity"].astype(int) < 0).all()
    sales = pos[pos["is_return"] == "0"]
    assert (sales["quantity"].astype(int) > 0).all()


def test_multiple_currencies_per_region(out):
    pos = read_all(out, "pos_transaction")
    assert pos.groupby("_region")["currency"].nunique().min() >= 2


def test_consent_has_missing_values(out):
    crm = read_all(out, "crm_client")
    assert crm["consent_share_cross_region"].isna().any()


def test_orphan_transactions_exist(out):
    crm = read_all(out, "crm_client")
    known = set(crm["client_id"])
    pos = read_all(out, "pos_transaction")
    ecom = read_all(out, "ecom_order")
    unknown = ~pd.concat([pos["client_id"], ecom["client_id"]]).isin(known)
    assert unknown.sum() >= 1


def test_duplicate_rows_are_resent(out):
    pos = read_all(out, "pos_transaction")
    dupes = pos.duplicated(subset=["transaction_id"], keep=False)
    assert dupes.sum() >= 2


def test_returns_within_14_days(out):
    pos = read_all(out, "pos_transaction")
    pos = pos[pos["transaction_id"].notna()].drop_duplicates("transaction_id")
    pos["d"] = pd.to_datetime(pos["transaction_ts"].str[:10], errors="coerce")
    sales = pos[pos["is_return"] == "0"]
    rets = pos[pos["is_return"] == "1"]
    assert len(rets) > 0
    m = rets.merge(sales, on=["client_id", "product_id"], suffixes=("_r", "_s"))
    m["gap"] = (m["d_r"] - m["d_s"]).dt.days
    # a return matches some earlier sale of the same product within 14 days
    ok = m[(m["gap"] >= 1) & (m["gap"] <= 14)]["transaction_id_r"].nunique()
    assert ok / len(rets) > 0.9


def test_some_repairs_happen_in_other_region(tmp_path):
    gd.generate(tmp_path, n_people=2500, seed=11, verbose=False)
    out = tmp_path
    t = read_all(out, "after_sales_ticket")
    assert "purchase_region" in t.columns
    assert (t["purchase_region"] != t["_region"]).sum() >= 1
    assert (t["purchase_region"] == t["_region"]).mean() > 0.8


def test_fx_has_no_weekends(out):
    fx = pd.read_csv(out / "raw" / "reference" / "fx_rate.csv", parse_dates=["rate_date"])
    assert (fx["rate_date"].dt.weekday < 5).all()
    assert set(fx["currency"]) == set(gd.BASE_EUR_PER_LOCAL)


def test_people_in_two_regions_have_truth_rows(out):
    truth = pd.read_csv(out / "truth" / "person_truth.csv")
    counts = truth.groupby("person_id")["client_id"].nunique()
    assert (counts == 2).sum() >= 5
    assert set(truth["record_type"]) == {"primary", "secondary"}


def test_same_seed_gives_same_output(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    gd.generate(a, n_people=120, seed=3, verbose=False)
    gd.generate(b, n_people=120, seed=3, verbose=False)

    def digest(folder):
        return hashlib.sha256((folder / "raw" / "_manifest.csv").read_bytes()).hexdigest()

    assert digest(a) == digest(b)
