#!/usr/bin/env python3
"""Synthetic data generator for Maison Cambon, a FICTIONAL luxury house.

Everything this script produces is made up. It is not real client data and it is
not data from any real company.

What it creates (default settings):
  * about 5,000 people, some registered in two regions (so identity matching is a real task)
  * three regions, each sending its own daily files: americas, europe, asia_pacific
  * about 100,000 sales rows over 12 months, plus returns, repairs and appointments
  * deliberate mess: late files, a schema change, duplicates, bad rows, missing consent

Output layout (under --out, default <repo>/data):
  raw/<region>/dt=YYYY-MM-DD/<table>.csv   daily files, exactly as a source system would send them
  raw/reference/                           product, boutique and fx_rate files
  raw/_manifest.csv                        what each file should contain and when it arrived
  truth/                                   the answer key, used only by tests (never loaded into Fabric)

Run:  python data_generator/generate_data.py
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# --------------------------------------------------------------------------- settings

DEFAULT_SEED = 42
DEFAULT_PEOPLE = 5000
DEFAULT_START = date(2025, 10, 1)
DEFAULT_DAYS = 365

REGION_ORDER = ["americas", "europe", "asia_pacific"]
REGION_WEIGHT = [0.38, 0.34, 0.28]
REGION_PREFIX = {"americas": "AM", "europe": "EU", "asia_pacific": "AP"}
REGION_PRICE_INDEX = {"americas": 1.05, "europe": 1.00, "asia_pacific": 1.10}
REGION_ECOM_SHARE = {"americas": 0.30, "europe": 0.28, "asia_pacific": 0.40}

# (boutique_id, city, country, region, currency)
BOUTIQUES = [
    ("AM-NYC-01", "New York", "US", "americas", "USD"),
    ("AM-NYC-02", "New York", "US", "americas", "USD"),
    ("AM-LAX-01", "Los Angeles", "US", "americas", "USD"),
    ("AM-MIA-01", "Miami", "US", "americas", "USD"),
    ("AM-YYZ-01", "Toronto", "CA", "americas", "CAD"),
    ("EU-PAR-01", "Paris", "FR", "europe", "EUR"),
    ("EU-PAR-02", "Paris", "FR", "europe", "EUR"),
    ("EU-LON-01", "London", "GB", "europe", "GBP"),
    ("EU-MIL-01", "Milan", "IT", "europe", "EUR"),
    ("EU-GVA-01", "Geneva", "CH", "europe", "CHF"),
    ("AP-SEL-01", "Seoul", "KR", "asia_pacific", "KRW"),
    ("AP-SEL-02", "Seoul", "KR", "asia_pacific", "KRW"),
    ("AP-TYO-01", "Tokyo", "JP", "asia_pacific", "JPY"),
    ("AP-HKG-01", "Hong Kong", "HK", "asia_pacific", "HKD"),
]

# Rough, made-up exchange rates (EUR per 1 unit of local currency)
BASE_EUR_PER_LOCAL = {
    "EUR": 1.0, "USD": 0.92, "CAD": 0.67, "GBP": 1.17,
    "CHF": 1.04, "KRW": 0.00068, "JPY": 0.0062, "HKD": 0.118,
}

# category -> sub_category -> (min price EUR, max price EUR, number of products)
CATALOG = {
    "Fashion": {
        "Leather Handbag": (3000, 9000, 14),
        "Ready-to-Wear Jacket": (1800, 6000, 14),
        "Dress": (1500, 5500, 12),
        "Shoes": (800, 1500, 12),
        "Accessories": (300, 900, 16),
    },
    "Watches and Jewelry": {
        "Watch": (4000, 40000, 10),
        "Fine Jewelry": (2500, 25000, 14),
        "Costume Jewelry": (400, 1800, 12),
    },
    "Fragrance and Beauty": {
        "Fragrance": (90, 420, 14),
        "Makeup": (40, 120, 18),
        "Skincare": (70, 380, 14),
    },
}
CATEGORIES = list(CATALOG.keys())
ADJECTIVES = ["Signature", "Classic", "Heritage", "Atelier", "Evening", "Riviera", "Studio",
              "Noir", "Ivory", "Pearl", "Linen", "Silk", "Midnight", "Golden", "Coastal"]

PERSONAS = ["vic", "high", "regular", "occasional", "prospect"]
PERSONA_P = [0.03, 0.10, 0.47, 0.30, 0.10]
PERSONA_LAMBDA = {"vic": 105, "high": 53, "regular": 26, "occasional": 8, "prospect": 0}
PERSONA_APPT = {"vic": 12, "high": 4, "regular": 0.5, "occasional": 0.1, "prospect": 0}
PERSONA_PRICE_ALPHA = {"vic": 0.5, "high": 0.3, "regular": 0.0, "occasional": -0.3, "prospect": 0.0}
PERSONA_ECOM_MULT = {"vic": 0.5, "high": 0.8, "regular": 1.0, "occasional": 1.0, "prospect": 1.0}
# weights for [Fashion, Watches and Jewelry, Fragrance and Beauty]
PERSONA_CAT_W = {
    "vic": [0.45, 0.40, 0.15], "high": [0.40, 0.25, 0.35],
    "regular": [0.30, 0.12, 0.58], "occasional": [0.25, 0.05, 0.70],
    "prospect": [0.3, 0.1, 0.6],
}

MULTI_REGION_SHARE = 0.06      # share of buying people who are registered in two regions
EUROPE_SCHEMA_CHANGE_DAY = 21  # week 3: europe crm_client gains client_segment
AMERICAS_SCHEMA_CHANGE_DAY = 120  # americas pos_transaction gains sales_associate_id

RATES = {
    "late_1_day": 0.03,        # a region's daily batch arrives one day late
    "late_3_days": 0.004,      # a region's batch is stuck and arrives three days late
    "truncated_file": 0.002,   # file has fewer rows than the manifest promises
    "resent_row": 0.004,       # row sent again the next day (exact duplicate)
    "orphan_client": 0.003,    # transaction points to a client that does not exist
    "null_price": 0.002,
    "unknown_product": 0.002,
    "future_dated": 0.001,
    "return_fashion_jewelry": 0.05,
    "return_beauty": 0.03,
    "ticket": 0.035,
    "cross_region_service": 0.15,  # share of repairs done in the other region, for two-region clients
    "consent_update": 0.03,
    "contact_update": 0.02,
    "missing_email": 0.05,
    "missing_phone": 0.08,
    "dirty_email": 0.05,       # upper case or trailing space
    "dirty_name": 0.02,        # all upper or all lower case
}

TABLES = ["crm_client", "pos_transaction", "ecom_order", "after_sales_ticket", "appointment"]

COLUMNS = {
    "crm_client": ["client_id", "region", "first_name", "last_name", "email", "phone",
                   "home_boutique_id", "created_at", "updated_at",
                   "consent_share_cross_region", "consent_marketing"],
    "pos_transaction": ["transaction_id", "client_id", "boutique_id", "product_id", "quantity",
                        "unit_price", "currency", "is_return", "transaction_ts"],
    "ecom_order": ["order_id", "client_id", "product_id", "quantity", "unit_price",
                   "currency", "is_return", "order_ts"],
    "after_sales_ticket": ["ticket_id", "client_id", "boutique_id", "product_id", "status",
                           "reason", "created_at", "closed_at", "purchase_region"],
    "appointment": ["appointment_id", "client_id", "boutique_id", "advisor_id",
                    "appointment_ts", "status"],
}

NSN_DIGITS = {"US": 10, "CA": 10, "FR": 9, "GB": 10, "IT": 10, "CH": 9, "KR": 10, "JP": 10, "HK": 8}
DIAL = {"US": "+1", "CA": "+1", "FR": "+33", "GB": "+44", "IT": "+39",
        "CH": "+41", "KR": "+82", "JP": "+81", "HK": "+852"}
EMAIL_DOMAINS = {
    "US": ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"],
    "CA": ["gmail.com", "rogers.com", "outlook.com"],
    "FR": ["gmail.com", "orange.fr", "free.fr", "outlook.fr"],
    "GB": ["gmail.com", "outlook.com", "btinternet.com"],
    "IT": ["gmail.com", "libero.it", "outlook.it"],
    "CH": ["bluewin.ch", "gmail.com", "outlook.com"],
    "KR": ["naver.com", "gmail.com", "daum.net"],
    "JP": ["gmail.com", "yahoo.co.jp", "icloud.com"],
    "HK": ["gmail.com", "yahoo.com.hk", "outlook.com"],
}
APAC_NAMES = {
    "KR": (["Min-jun", "Seo-yeon", "Ji-woo", "Ha-eun", "Do-yun", "Su-bin", "Ye-jin", "Hyun-woo", "Ji-min", "Soo-ah"],
           ["Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang", "Lim"]),
    "JP": (["Haruto", "Yui", "Sota", "Hina", "Ren", "Mio", "Aoi", "Riku", "Sakura", "Yuto"],
           ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi", "Kato"]),
    "HK": (["Wing", "Mei", "Ka-man", "Hoi", "Tsz-ching", "Yan", "Siu-ming", "Pui", "Hiu", "Lok"],
           ["Chan", "Wong", "Lee", "Cheung", "Lau", "Ho", "Leung", "Ng", "Tang", "Yip"]),
}
NICKNAMES = {"alexandra": "Alex", "katherine": "Kate", "elizabeth": "Liz", "jennifer": "Jenny",
             "michael": "Mike", "christopher": "Chris", "william": "Bill", "robert": "Rob",
             "stephanie": "Steph", "nicholas": "Nick", "margaret": "Peggy", "richard": "Rick"}
TICKET_REASONS = ["repair", "resize", "authentication", "exchange", "complaint", "cleaning"]


# --------------------------------------------------------------------------- small helpers

def fold(text: str) -> str:
    """Lower case and remove accents."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def nice_price(x: float) -> float:
    """Round to a clean 'price list' number whatever the currency size."""
    if x <= 0:
        return 0
    step = max(1.0, 10 ** (math.floor(math.log10(x)) - 2))
    return round(x / step) * step


def num(x):
    """Whole numbers print as integers, others with 2 decimals."""
    return int(x) if float(x).is_integer() else round(float(x), 2)


def format_phone(country: str, digits: str, style: int) -> str:
    dial = DIAL[country]
    if style == 0:
        return f"{dial}{digits}"
    if style == 1:
        groups = [digits[i:i + 3] for i in range(0, len(digits), 3)]
        return f"{dial} {' '.join(groups)}"
    if country in ("US", "CA"):
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if country == "HK":
        return digits
    return f"0{digits}"


# --------------------------------------------------------------------------- generator

class Generator:
    def __init__(self, out_dir, n_people, seed, start, days, verbose):
        self.out = Path(out_dir)
        self.n_people = n_people
        self.seed = seed
        self.start = start
        self.days = days
        self.verbose = verbose
        self.rng = np.random.default_rng(seed)
        Faker.seed(seed)
        self.fakers = {"US": Faker("en_US"), "FR": Faker("fr_FR"),
                       "IT": Faker("it_IT"), "GB": Faker("en_GB")}
        self.issues = defaultdict(int)
        self.used_emails: set[str] = set()
        self.rows_sent = defaultdict(int)

    # ----- tiny random helpers
    def pick(self, seq):
        return seq[int(self.rng.integers(len(seq)))]

    def chance(self, p):
        return self.rng.random() < p

    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def ts(self, day_idx: int, seconds: int) -> str:
        d = datetime(self.start.year, self.start.month, self.start.day)
        return (d + timedelta(days=day_idx, seconds=int(seconds))).strftime("%Y-%m-%d %H:%M:%S")

    # ===================================================================== reference data
    def build_reference(self):
        rng = self.rng
        self.boutiques = [dict(boutique_id=b[0], city=b[1], country=b[2], region=b[3], currency=b[4])
                          for b in BOUTIQUES]
        self.by_region = {r: [b for b in self.boutiques if b["region"] == r] for r in REGION_ORDER}
        self.boutique_by_id = {b["boutique_id"]: b for b in self.boutiques}
        self.advisors = {b["boutique_id"]: [f"{b['boutique_id']}-A{k:02d}" for k in range(1, 7)]
                         for b in self.boutiques}
        self.ccy_region = {b["currency"]: b["region"] for b in self.boutiques}

        products, n = [], 0
        for cat, subs in CATALOG.items():
            for sub, (lo, hi, count) in subs.items():
                for _ in range(count):
                    n += 1
                    price = nice_price(math.exp(rng.uniform(math.log(lo), math.log(hi))))
                    products.append(dict(product_id=f"PRD{n:04d}", category=cat, sub_category=sub,
                                         name=f"{self.pick(ADJECTIVES)} {sub} (Ref {n:03d})",
                                         list_price_eur=num(price)))
        self.products = products

        # Popularity inside each category (a few best sellers, a long tail)
        self.cat_products = {}
        self.pw_cache = {}
        for cat in CATEGORIES:
            items = [p for p in products if p["category"] == cat]
            ids = [p["product_id"] for p in items]
            prices = np.array([p["list_price_eur"] for p in items], dtype=float)
            ranks = rng.permutation(len(items)) + 1
            self.cat_products[cat] = (ids, prices, 1.0 / ranks ** 0.8)
        for persona in PERSONAS:
            for cat in CATEGORIES:
                ids, prices, zipf = self.cat_products[cat]
                w = zipf * prices ** PERSONA_PRICE_ALPHA[persona]
                self.pw_cache[(cat, persona)] = w / w.sum()

        # Local price lists: fixed per currency (like a real price list), not recalculated daily
        self.price_local = {}
        for p in products:
            self.price_local[p["product_id"]] = {}
            for ccy, base in BASE_EUR_PER_LOCAL.items():
                idx = REGION_PRICE_INDEX[self.ccy_region.get(ccy, "europe")]
                self.price_local[p["product_id"]][ccy] = num(nice_price(p["list_price_eur"] * idx / base))
        self.product_category = {p["product_id"]: p["category"] for p in products}

        # Exchange rates drift gently around the base rate
        self.fx = {}
        for ccy, base in BASE_EUR_PER_LOCAL.items():
            if ccy == "EUR":
                self.fx[ccy] = np.ones(self.days)
                continue
            x, vals = 0.0, []
            for _ in range(self.days):
                x = x * 0.97 + rng.normal(0, 0.004)
                vals.append(base * math.exp(x))
            self.fx[ccy] = np.array(vals)

        # Busy days: weekends and the holiday season sell more
        month_w = {1: 0.8, 2: 1.1, 3: 0.9, 4: 1.0, 5: 1.1, 6: 0.9, 7: 0.8, 8: 0.7, 9: 1.0, 10: 1.0, 11: 1.2, 12: 1.8}
        dow_w = [0.8, 0.8, 0.85, 0.9, 1.0, 1.6, 1.1]
        w = np.array([month_w[(self.start + timedelta(d)).month] * dow_w[(self.start + timedelta(d)).weekday()]
                      for d in range(self.days)])
        self.day_cum = np.cumsum(w / w.sum())
        self.day_cum[-1] = 1.0

    def draw_days(self, first_idx: int, n: int):
        c0 = float(self.day_cum[first_idx - 1]) if first_idx > 0 else 0.0
        u = self.rng.uniform(c0, 1.0, n)
        return np.minimum(np.searchsorted(self.day_cum, u, side="right"), self.days - 1)

    # ===================================================================== people and CRM
    def draw_name(self, country):
        if country in APAC_NAMES:
            first, last = APAC_NAMES[country]
            return self.pick(first), self.pick(last)
        key = {"US": "US", "CA": "US", "FR": "FR", "CH": "FR", "IT": "IT", "GB": "GB"}[country]
        fk = self.fakers[key]
        return fk.first_name(), fk.last_name()

    def make_email(self, first, last, country):
        base = re.sub(r"[^a-z0-9.]", "", f"{fold(first)}.{fold(last)}")
        while True:
            email = f"{base}{int(self.rng.integers(1, 100))}@{self.pick(EMAIL_DOMAINS[country])}"
            if email not in self.used_emails:
                self.used_emails.add(email)
                return email

    def make_digits(self, country):
        n = NSN_DIGITS[country]
        return str(int(self.rng.integers(2, 10))) + "".join(str(int(d)) for d in self.rng.integers(0, 10, n - 1))

    def name_variant(self, first, last):
        rng = self.rng

        def typo(s):
            if len(s) < 4:
                return s
            i = int(rng.integers(1, len(s) - 1))
            op = int(rng.integers(0, 3))
            if op == 0:
                return s[:i] + s[i + 1] + s[i] + s[i + 2:]
            if op == 1:
                return s[:i] + s[i + 1:]
            return s[:i] + s[i] + s[i:]

        r = rng.random()
        if r < 0.35:
            return (typo(first), last, "typo") if self.chance(0.5) else (first, typo(last), "typo")
        if r < 0.50:
            if fold(first) != first.lower() or fold(last) != last.lower():
                return fold(first).title(), fold(last).title(), "accent"
            return first, typo(last), "typo"
        if r < 0.70:
            return NICKNAMES.get(first.lower(), first[:4]), last, "nickname"
        if r < 0.85:
            return last, first, "swap"
        return first[0] + ".", last, "initial"

    def new_consent(self):
        share = self.pick_p(["1", "0", None], [0.55, 0.41, 0.04])
        marketing = self.pick_p(["1", "0", None], [0.62, 0.34, 0.04])
        return share, marketing

    def pick_p(self, seq, p):
        return seq[int(self.rng.choice(len(seq), p=p))]

    def draw_created(self, persona):
        rng = self.rng
        if persona == "prospect" and self.chance(0.4):
            return -int(rng.integers(1100, 1826))   # old prospects, eligible for the 3 year retention job
        if rng.random() < 0.70:
            return -int(rng.integers(1, 1096))
        return int(rng.integers(0, self.days))

    def build_people(self):
        rng = self.rng
        self.people = []
        for i in range(self.n_people):
            region = REGION_ORDER[int(rng.choice(3, p=REGION_WEIGHT))]
            persona = PERSONAS[int(rng.choice(len(PERSONAS), p=PERSONA_P))]
            home_b = self.pick(self.by_region[region])
            country = home_b["country"]
            first, last = self.draw_name(country)
            email = self.make_email(first, last, country)
            digits = self.make_digits(country)
            person = dict(person_id=f"P{i + 1:05d}", persona=persona, region=region, country=country,
                          first=first, last=last, email=email, digits=digits, records=[])
            share, marketing = self.new_consent()
            person["records"].append(self.make_record(
                person, region, home_b, self.draw_created(persona), first, last, email,
                format_phone(country, digits, int(rng.choice(3, p=[0.7, 0.2, 0.1]))),
                share, marketing, "primary", "none", True, True))

            if persona != "prospect" and self.chance(MULTI_REGION_SHARE):
                other = self.pick([r for r in REGION_ORDER if r != region])
                b2 = self.pick(self.by_region[other])
                c2 = b2["country"]
                f2, l2, variant = self.name_variant(first, last)
                email_same = self.chance(0.5)
                phone_same = self.chance(0.6)
                e2 = email if email_same else self.make_email(first, last, c2)
                p2 = (format_phone(country, digits, int(rng.integers(0, 2))) if phone_same
                      else format_phone(c2, self.make_digits(c2), int(rng.choice(3, p=[0.7, 0.2, 0.1]))))
                share2, marketing2 = share, marketing
                if self.chance(0.2):  # the two regions disagree about consent
                    share2 = "0" if share == "1" else "1"
                    self.issues["consent_conflicts_between_regions"] += 1
                person["records"].append(self.make_record(
                    person, other, b2, int(rng.integers(0, 300)), f2, l2, e2, p2,
                    share2, marketing2, "secondary", variant, email_same, phone_same))
                self.issues["people_in_two_regions"] += 1
            self.people.append(person)

        # Client ids are numbered by creation date inside each region
        for region in REGION_ORDER:
            recs = [r for p in self.people for r in p["records"] if r["region"] == region]
            recs.sort(key=lambda r: (r["created_idx"], r["tiebreak"]))
            for n, r in enumerate(recs, 1):
                r["client_id"] = f"{REGION_PREFIX[region]}-{n:06d}"
        self.log(f"  people: {len(self.people)}, crm records: "
                 f"{sum(len(p['records']) for p in self.people)}, "
                 f"in two regions: {self.issues['people_in_two_regions']}")

    def make_record(self, person, region, boutique, created_idx, first, last, email, phone,
                    share, marketing, rtype, variant, email_same, phone_same):
        rng = self.rng
        if self.chance(RATES["missing_email"]):
            email = None
        elif self.chance(RATES["dirty_email"]):
            email = email.upper() if self.chance(0.5) else email + " "
            self.issues["dirty_emails"] += 1
        if self.chance(RATES["missing_phone"]):
            phone = None
        if self.chance(RATES["dirty_name"]):
            first, last = (first.upper(), last.upper()) if self.chance(0.5) else (first.lower(), last.lower())
            self.issues["dirty_names"] += 1
        if share is None or marketing is None:
            self.issues["missing_consent_values"] += 1
        b_ids = [b["boutique_id"] for b in self.by_region[region]]
        others = (1 - 0.6) / max(len(b_ids) - 1, 1)
        b_p = [0.6 if bid == boutique["boutique_id"] else others for bid in b_ids]
        b_p = np.array(b_p) / sum(b_p)
        rec = dict(region=region, record_type=rtype, boutique=boutique, created_idx=created_idx,
                   first=first, last=last, email=email, phone=phone, share=share, marketing=marketing,
                   variant=variant, email_same=email_same, phone_same=phone_same, b_ids=b_ids, b_p=b_p,
                   tiebreak=float(rng.random()), created_seconds=int(rng.integers(0, 86400)),
                   ecom_ccy=boutique["currency"], person_id=person["person_id"],
                   client_segment=None, client_id=None)
        if region == "europe":
            # A source-system hint about the client. The gold layer works out its own VIC tier from spend.
            rec["client_segment"] = {"vic": "vic", "high": "priority"}.get(
                person["persona"], "core" if self.chance(0.3) and person["persona"] == "regular" else None)

        updates = []
        lo = max(created_idx, 0) + 1
        if lo < self.days - 1:
            if self.chance(RATES["consent_update"]):
                new = "0" if share == "1" else "1"
                updates.append((int(rng.integers(lo, self.days)), "share", new))
                self.issues["consent_changes_during_period"] += 1
            if self.chance(RATES["contact_update"]):
                if self.chance(0.5):
                    updates.append((int(rng.integers(lo, self.days)), "phone",
                                    format_phone(person["country"], self.make_digits(person["country"]), 0)))
                else:
                    updates.append((int(rng.integers(lo, self.days)), "email",
                                    self.make_email(first, last, person["country"])))
        updates.sort(key=lambda u: u[0])
        state = dict(eff_idx=created_idx, share=share, marketing=marketing, email=email, phone=phone)
        versions = [dict(state)]
        for idx, field, value in updates:
            state = {**state, "eff_idx": idx, field: value}
            versions.append(dict(state))
        rec["versions"] = versions
        return rec

    # ===================================================================== activity
    def build_activity(self):
        rng = self.rng
        days = self.days
        self.txns, self.tickets, self.appts = [], [], []
        for person in self.people:
            persona = person["persona"]
            if persona == "prospect":
                continue
            recs = person["records"]
            first_idx = max(0, min(r["created_idx"] for r in recs))
            frac = (days - first_idx) / days

            n = int(rng.poisson(PERSONA_LAMBDA[persona] * frac))
            if n > 0:
                k = int(rng.choice([1, 2, 3], p=[0.35, 0.45, 0.20]))
                w = np.array(PERSONA_CAT_W[persona])
                allowed = rng.choice(3, size=k, replace=False, p=w / w.sum())
                aw = w[allowed] / w[allowed].sum()
                cat_idx = rng.choice(allowed, size=n, p=aw)
                day_idx = self.draw_days(first_idx, n)

                prods = [None] * n
                for ci in set(cat_idx.tolist()):
                    positions = [j for j in range(n) if cat_idx[j] == ci]
                    cat = CATEGORIES[ci]
                    ids = self.cat_products[cat][0]
                    sel = rng.choice(len(ids), size=len(positions), p=self.pw_cache[(cat, persona)])
                    for pos, s in zip(positions, sel):
                        prods[pos] = ids[int(s)]

                for j in range(n):
                    idx = int(day_idx[j])
                    elig = [r for r in recs if max(r["created_idx"], 0) <= idx]
                    rec = elig[0] if len(elig) == 1 else (recs[0] if rng.random() < 0.6 else recs[1])
                    pid = prods[j]
                    cat = self.product_category[pid]
                    qty = 1
                    if cat == "Fragrance and Beauty":
                        r = rng.random()
                        qty = 1 if r < 0.80 else (2 if r < 0.95 else 3)
                    ecom_p = REGION_ECOM_SHARE[rec["region"]] * PERSONA_ECOM_MULT[persona]
                    channel = "ecom" if rng.random() < ecom_p else "pos"
                    if channel == "pos":
                        boutique_id = rec["b_ids"][int(rng.choice(len(rec["b_ids"]), p=rec["b_p"]))]
                        currency = self.boutique_by_id[boutique_id]["currency"]
                        secs = int(rng.integers(10 * 3600, 19 * 3600))
                    else:
                        boutique_id = None
                        currency = rec["ecom_ccy"]
                        secs = int(rng.integers(8 * 3600, 24 * 3600))
                    row = dict(region=rec["region"], channel=channel, idx=idx, secs=secs, rec=rec,
                               boutique_id=boutique_id, product_id=pid, quantity=qty,
                               unit_price=self.price_local[pid][currency], currency=currency, is_return=0,
                               sales_associate_id=(self.pick(self.advisors[boutique_id]) if boutique_id else None))
                    self.txns.append(row)

                    ret_p = RATES["return_beauty"] if cat == "Fragrance and Beauty" else RATES["return_fashion_jewelry"]
                    if rng.random() < ret_p:
                        ridx = idx + int(rng.integers(1, 15))  # 14-day return window
                        if ridx <= days - 1:
                            ret = dict(row, idx=ridx, quantity=-qty, is_return=1,
                                       secs=int(rng.integers(10 * 3600, 19 * 3600)))
                            self.txns.append(ret)

                    if cat != "Fragrance and Beauty" and rng.random() < RATES["ticket"]:
                        cidx = idx + int(rng.integers(5, 121))
                        if cidx <= days - 1:
                            age = days - 1 - cidx
                            p = [0.5, 0.35, 0.15] if age < 20 else [0.05, 0.10, 0.85]
                            status = self.pick_p(["open", "in_progress", "closed"], p)
                            closed_ts = None
                            if status == "closed":
                                closed_ts = self.ts(min(days - 1, cidx + int(rng.integers(3, 61))),
                                                    int(rng.integers(9 * 3600, 18 * 3600)))
                            # A few repairs happen in the other region, for clients who have a record there.
                            svc = rec
                            if len(recs) == 2 and rng.random() < RATES["cross_region_service"]:
                                other = recs[1] if rec is recs[0] else recs[0]
                                if max(other["created_idx"], 0) <= cidx:
                                    svc = other
                                    self.issues["cross_region_repairs"] += 1
                            svc_boutique = (boutique_id if svc is rec and boutique_id
                                            else svc["boutique"]["boutique_id"])
                            self.tickets.append(dict(
                                region=svc["region"], idx=cidx, rec=svc, purchase_region=rec["region"],
                                boutique_id=svc_boutique, product_id=pid,
                                status=status, reason=self.pick(TICKET_REASONS),
                                created_ts=self.ts(cidx, int(rng.integers(9 * 3600, 18 * 3600))),
                                closed_ts=closed_ts))

            rec = recs[0]
            na = int(rng.poisson(PERSONA_APPT[persona] * frac))
            if na > 0:
                for idx in self.draw_days(first_idx, na):
                    idx = int(idx)
                    bid = rec["b_ids"][int(rng.choice(len(rec["b_ids"]), p=rec["b_p"]))]
                    self.appts.append(dict(
                        region=rec["region"], idx=idx, rec=rec, boutique_id=bid,
                        advisor_id=self.pick(self.advisors[bid]),
                        secs=int(rng.integers(10 * 3600, 18 * 3600)),
                        status=self.pick_p(["completed", "cancelled", "no_show"], [0.82, 0.12, 0.06])))

        # Give every row its id, in time order inside each region
        counters = defaultdict(int)
        self.txns.sort(key=lambda r: (r["region"], r["channel"], r["idx"], r["secs"]))
        for r in self.txns:
            key = (r["region"], r["channel"])
            counters[key] += 1
            tag = "POS" if r["channel"] == "pos" else "WEB"
            r["id"] = f"{REGION_PREFIX[r['region']]}-{tag}-{counters[key]:08d}"
        self.tickets.sort(key=lambda r: (r["region"], r["idx"]))
        self.appts.sort(key=lambda r: (r["region"], r["idx"], r["secs"]))
        for lst, tag in ((self.tickets, "TKT"), (self.appts, "APT")):
            c = defaultdict(int)
            for r in lst:
                c[r["region"]] += 1
                r["id"] = f"{REGION_PREFIX[r['region']]}-{tag}-{c[r['region']]:07d}"
        self.log(f"  sales and returns: {len(self.txns)}, tickets: {len(self.tickets)}, appointments: {len(self.appts)}")

    # ===================================================================== output
    def build_buckets(self):
        rng = self.rng
        b = {r: {t: defaultdict(list) for t in TABLES} for r in REGION_ORDER}

        for person in self.people:
            for rec in person["records"]:
                for v in rec["versions"]:
                    day = max(v["eff_idx"], 0)
                    created = self.ts(rec["created_idx"], rec["created_seconds"])
                    updated = created if v is rec["versions"][0] else self.ts(
                        v["eff_idx"], int(rng.integers(0, 86400)))
                    row = dict(client_id=rec["client_id"], region=rec["region"], first_name=rec["first"],
                               last_name=rec["last"], email=v["email"], phone=v["phone"],
                               home_boutique_id=rec["boutique"]["boutique_id"], created_at=created,
                               updated_at=updated, consent_share_cross_region=v["share"],
                               consent_marketing=v["marketing"], client_segment=rec["client_segment"])
                    b[rec["region"]]["crm_client"][day].append(row)

        for r in self.txns:
            rec = r["rec"]
            common = dict(client_id=rec["client_id"], product_id=r["product_id"], quantity=r["quantity"],
                          unit_price=r["unit_price"], currency=r["currency"], is_return=r["is_return"])
            ts = self.ts(r["idx"], r["secs"])
            if r["channel"] == "pos":
                row = dict(transaction_id=r["id"], boutique_id=r["boutique_id"], transaction_ts=ts,
                           sales_associate_id=r["sales_associate_id"], **common)
                b[r["region"]]["pos_transaction"][r["idx"]].append(row)
            else:
                row = dict(order_id=r["id"], order_ts=ts, **common)
                b[r["region"]]["ecom_order"][r["idx"]].append(row)

        for t in self.tickets:
            b[t["region"]]["after_sales_ticket"][t["idx"]].append(dict(
                ticket_id=t["id"], client_id=t["rec"]["client_id"], boutique_id=t["boutique_id"],
                product_id=t["product_id"], status=t["status"], reason=t["reason"],
                created_at=t["created_ts"], closed_at=t["closed_ts"], purchase_region=t["purchase_region"]))
        for a in self.appts:
            b[a["region"]]["appointment"][a["idx"]].append(dict(
                appointment_id=a["id"], client_id=a["rec"]["client_id"], boutique_id=a["boutique_id"],
                advisor_id=a["advisor_id"], appointment_ts=self.ts(a["idx"], a["secs"]), status=a["status"]))
        return b

    def corrupt(self, table, region, row):
        """Inject bad rows. Called once per transaction row, in a fixed order, so runs repeat exactly."""
        rng = self.rng
        if rng.random() < RATES["orphan_client"]:
            row["client_id"] = f"{REGION_PREFIX[region]}-9{int(rng.integers(0, 100000)):05d}"
            self.issues["orphan_client_ids"] += 1
        if rng.random() < RATES["null_price"]:
            row["unit_price"] = None
            self.issues["null_prices"] += 1
        if rng.random() < RATES["unknown_product"]:
            row["product_id"] = f"PRDX{int(rng.integers(0, 10000)):04d}"
            self.issues["unknown_products"] += 1
        if rng.random() < RATES["future_dated"]:
            col = "transaction_ts" if table == "pos_transaction" else "order_ts"
            shifted = datetime.strptime(row[col], "%Y-%m-%d %H:%M:%S") + timedelta(days=30)
            row[col] = shifted.strftime("%Y-%m-%d %H:%M:%S")
            self.issues["future_dated_rows"] += 1

    def columns_for(self, table, region, day):
        cols = list(COLUMNS[table])
        if table == "crm_client" and region == "europe" and day >= EUROPE_SCHEMA_CHANGE_DAY:
            cols.append("client_segment")
        if table == "pos_transaction" and region == "americas" and day >= AMERICAS_SCHEMA_CHANGE_DAY:
            cols.append("sales_associate_id")
        return cols

    def write_reference(self):
        ref = self.out / "raw" / "reference"
        ref.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.products).to_csv(ref / "product.csv", index=False)
        pd.DataFrame(self.boutiques).to_csv(ref / "boutique.csv", index=False)
        rows = []
        for d in range(self.days):
            day = self.start + timedelta(d)
            if day.weekday() >= 5:      # no rates on weekends: the pipeline must carry the last rate forward
                continue
            for ccy, arr in self.fx.items():
                rows.append(dict(rate_date=day.isoformat(), currency=ccy,
                                 rate_to_eur=f"{arr[d]:.8f}".rstrip("0").rstrip(".")))
        pd.DataFrame(rows).to_csv(ref / "fx_rate.csv", index=False)

    def write_raw(self, buckets):
        rng = self.rng
        manifest = []
        prev_sent = {}
        for region in REGION_ORDER:
            for d in range(self.days):
                dt = self.start + timedelta(d)
                batch_lag = None
                for table in TABLES:
                    rows = [dict(r) for r in buckets[region][table].get(d, [])]
                    if table in ("pos_transaction", "ecom_order"):
                        for r in rows:
                            self.corrupt(table, region, r)
                    if table in ("pos_transaction", "ecom_order", "after_sales_ticket"):
                        prev = prev_sent.get((region, table), [])
                        if prev:
                            mask = rng.random(len(prev)) < RATES["resent_row"]
                            for r, m in zip(prev, mask):
                                if m:
                                    rows.append(dict(r))
                                    self.issues["resent_duplicate_rows"] += 1
                        prev_sent[(region, table)] = [dict(r) for r in rows]
                    if not rows:
                        continue

                    if batch_lag is None:
                        x = rng.random()
                        batch_lag = 3 if x < RATES["late_3_days"] else (1 if x < RATES["late_3_days"] + RATES["late_1_day"] else 0)
                        if batch_lag:
                            self.issues["late_batches"] += 1
                    expected = datetime(dt.year, dt.month, dt.day) + timedelta(days=1, hours=2)
                    actual = expected + timedelta(days=batch_lag, minutes=int(rng.integers(0, 90)))

                    promised = len(rows)
                    if promised >= 5 and rng.random() < RATES["truncated_file"]:
                        rows = rows[:-2]
                        self.issues["truncated_files"] += 1

                    cols = self.columns_for(table, region, d)
                    folder = self.out / "raw" / region / f"dt={dt.isoformat()}"
                    folder.mkdir(parents=True, exist_ok=True)
                    pd.DataFrame(rows, columns=cols, dtype=object).to_csv(folder / f"{table}.csv", index=False)
                    self.rows_sent[(region, table)] += len(rows)
                    manifest.append(dict(region=region, dt=dt.isoformat(), table=table,
                                         file_path=f"{region}/dt={dt.isoformat()}/{table}.csv",
                                         row_count=promised,
                                         expected_arrival_ts=expected.strftime("%Y-%m-%d %H:%M:%S"),
                                         actual_arrival_ts=actual.strftime("%Y-%m-%d %H:%M:%S")))
            self.log(f"  wrote region {region}")
        pd.DataFrame(manifest).to_csv(self.out / "raw" / "_manifest.csv", index=False)
        self.n_files = len(manifest)

    def write_truth(self):
        truth = self.out / "truth"
        truth.mkdir(parents=True, exist_ok=True)
        rows = []
        for p in self.people:
            for r in p["records"]:
                rows.append(dict(person_id=p["person_id"], persona=p["persona"], home_region=p["region"],
                                 region=r["region"], client_id=r["client_id"], record_type=r["record_type"],
                                 name_variant=r["variant"], email_same_as_primary=r["email_same"],
                                 phone_same_as_primary=r["phone_same"],
                                 created_date=(self.start + timedelta(r["created_idx"])).isoformat()))
        pd.DataFrame(rows).to_csv(truth / "person_truth.csv", index=False)
        summary = dict(
            seed=self.seed, start=self.start.isoformat(), days=self.days, people=len(self.people),
            crm_records=len(rows), files=self.n_files,
            rows_sent={f"{r}/{t}": n for (r, t), n in sorted(self.rows_sent.items())},
            personas={p: sum(1 for x in self.people if x["persona"] == p) for p in PERSONAS},
            injected_issues=dict(sorted(self.issues.items())),
            schema_changes=[
                f"europe crm_client gains client_segment from day {EUROPE_SCHEMA_CHANGE_DAY}",
                f"americas pos_transaction gains sales_associate_id from day {AMERICAS_SCHEMA_CHANGE_DAY}"])
        (truth / "summary.json").write_text(json.dumps(summary, indent=2))
        return summary

    def run(self):
        for sub in ("raw", "truth"):
            if (self.out / sub).exists():
                shutil.rmtree(self.out / sub)
        self.log("Building reference data")
        self.build_reference()
        self.log("Building people and CRM records")
        self.build_people()
        self.log("Building sales, returns, repairs and appointments")
        self.build_activity()
        self.log("Writing files")
        self.write_reference()
        self.write_raw(self.build_buckets())
        return self.write_truth()


def generate(out_dir, n_people=DEFAULT_PEOPLE, seed=DEFAULT_SEED, start=DEFAULT_START,
             days=DEFAULT_DAYS, verbose=True):
    """Create the full synthetic dataset and return a summary dictionary."""
    return Generator(out_dir, n_people, seed, start, days, verbose).run()


def main():
    repo_root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Generate synthetic Maison Cambon data (fictional).")
    ap.add_argument("--out", default=str(repo_root / "data"), help="output folder (default: <repo>/data)")
    ap.add_argument("--people", type=int, default=DEFAULT_PEOPLE)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--start", default=DEFAULT_START.isoformat(), help="first day, YYYY-MM-DD")
    args = ap.parse_args()
    summary = generate(args.out, args.people, args.seed, date.fromisoformat(args.start))
    print("\nDone.")
    print(f"  people: {summary['people']}, crm records: {summary['crm_records']}, files: {summary['files']}")
    for k, v in summary["rows_sent"].items():
        print(f"  {k:<36}{v:>8}")
    print("  injected problems:")
    for k, v in summary["injected_issues"].items():
        print(f"    {k:<36}{v:>6}")


if __name__ == "__main__":
    main()
