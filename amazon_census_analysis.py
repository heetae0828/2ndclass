import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent
AMAZON_CSV = DATA_DIR / "amazon-purchases.csv"
SURVEY_CSV = DATA_DIR / "survey.csv"
ACS_CSV = DATA_DIR / "acs_2022_state_profile.csv"
MERGED_CSV = DATA_DIR / "amazon_acs_state_profile.csv"
SURVEY_SUMMARY_CSV = DATA_DIR / "survey_state_summary.csv"
SURVEY_BIAS_CSV = DATA_DIR / "survey_bias_vs_acs.csv"
CATEGORY_SHARE_CSV = DATA_DIR / "amazon_state_category_share.csv"

DEFAULT_CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "d943b8a3d7a2c400ab10ac45f2c9746c8ceec766")

STATE_NAME_TO_ABBR = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "Puerto Rico": "PR",
}

INCOME_BAND_TO_MID = {
    "Less than $25,000": 20000,
    "$25,000 - $49,999": 37500,
    "$50,000 - $74,999": 62500,
    "$75,000 - $99,999": 87500,
    "$100,000 - $149,999": 125000,
    "$150,000 or more": 175000,
    "Prefer not to say": np.nan,
}

CATEGORY_KEYWORDS = {
    "health_premium": ["HEALTH", "SUPPLEMENT", "VITAMIN", "ORGANIC", "WELLNESS", "NUTRITION", "PROTEIN"],
    "book_education": ["BOOK", "READ", "EBOOK", "EDUCATION", "LEARNING", "SCHOOL"],
    "electronics": ["ELECTRONIC", "COMPUTER", "TABLET", "TV", "AUDIO", "HEADPHONES", "CAMERA", "PHONE", "ROBOT", "DRIVE", "STORAGE", "MOUSE", "KEYBOARD"],
}


def clean_state(code_or_name: str) -> str:
    if pd.isna(code_or_name):
        return ""
    value = str(code_or_name).strip()
    if len(value) == 2 and value.isalpha():
        return value.upper()
    return STATE_NAME_TO_ABBR.get(value.title(), "")


def fetch_census_data(api_key: str, year: int = 2022) -> pd.DataFrame:
    variables = [
        "NAME",
        "B19013_001E",  # median household income
        "B01002_001E",  # median age
        "B15003_001E",  # total population 25+ for education
        "B15003_022E",  # Bachelor's degree
        "B15003_023E",  # Master's degree
        "B15003_024E",  # Professional school degree
        "B15003_025E",  # Doctorate degree
        "B17001_001E",  # poverty universe
        "B17001_002E",  # below poverty
        "B03002_001E",  # total population for race/ethnicity
        "B03002_002E",  # White alone
        "B03002_003E",  # Black or African American alone
        "B03002_012E",  # Hispanic or Latino
        "B23025_003E",  # civilian labor force
        "B23025_005E",  # employed
    ]
    field_string = ",".join(variables)
    url = (
        f"https://api.census.gov/data/{year}/acs/acs5?get={urllib.parse.quote(field_string)}"
        f"&for=state:*&key={urllib.parse.quote(api_key)}"
    )

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Census API HTTP error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Census API connection error: {exc}") from exc

    data = json.loads(body)
    df = pd.DataFrame(data[1:], columns=data[0])
    numeric_cols = [c for c in df.columns if c not in {"NAME", "state"}]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df["State"] = df["state"].astype(str).str.zfill(2)
    df["median_household_income"] = df["B19013_001E"]
    df["median_age"] = df["B01002_001E"]
    df["pct_bachelor_degree_or_higher"] = (
        df[["B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E"]].sum(axis=1)
        / df["B15003_001E"]
        * 100
    )
    df["pct_below_poverty_line"] = df["B17001_002E"] / df["B17001_001E"] * 100
    df["pct_hispanic"] = df["B03002_012E"] / df["B03002_001E"] * 100
    df["pct_white"] = df["B03002_002E"] / df["B03002_001E"] * 100
    df["pct_black"] = df["B03002_003E"] / df["B03002_001E"] * 100
    df["pct_employed"] = np.where(
        df["B23025_003E"] > 0,
        df["B23025_005E"] / df["B23025_003E"] * 100,
        np.nan,
    )
    df = df[[
        "State",
        "NAME",
        "median_household_income",
        "median_age",
        "pct_bachelor_degree_or_higher",
        "pct_below_poverty_line",
        "pct_hispanic",
        "pct_white",
        "pct_black",
        "pct_employed",
    ]]
    return df


def load_amazon_data() -> pd.DataFrame:
    if not AMAZON_CSV.exists():
        raise FileNotFoundError(f"Amazon purchases file not found: {AMAZON_CSV}")
    amazon_df = pd.read_csv(
        AMAZON_CSV,
        dtype={
            "Order Date": str,
            "Purchase Price Per Unit": str,
            "Quantity": str,
            "Shipping Address State": str,
            "Title": str,
            "ASIN/ISBN (Product Code)": str,
            "Category": str,
            "Survey ResponseID": str,
        },
        low_memory=False,
    )
    amazon_df["Purchase Price Per Unit"] = pd.to_numeric(
        amazon_df["Purchase Price Per Unit"], errors="coerce"
    )
    amazon_df["Quantity"] = pd.to_numeric(amazon_df["Quantity"], errors="coerce").fillna(1)
    amazon_df["State"] = (
        amazon_df["Shipping Address State"].astype(str).str.strip().str.upper()
    )
    amazon_df = amazon_df[amazon_df["State"].isin(STATE_NAME_TO_ABBR.values())].copy()
    amazon_df["Spend"] = amazon_df["Purchase Price Per Unit"] * amazon_df["Quantity"]
    amazon_df["Category"] = amazon_df["Category"].fillna("UNKNOWN")
    return amazon_df


def load_survey_data() -> pd.DataFrame:
    if not SURVEY_CSV.exists():
        raise FileNotFoundError(f"Survey file not found: {SURVEY_CSV}")
    survey_df = pd.read_csv(SURVEY_CSV, dtype=str, low_memory=False)
    survey_df["State"] = survey_df["Q-demos-state"].astype(str).str.strip().replace("nan", "")
    survey_df["State Abbrev"] = survey_df["State"].map(STATE_NAME_TO_ABBR).fillna("")
    survey_df["Income Band Approx"] = survey_df["Q-demos-income"].map(INCOME_BAND_TO_MID)
    return survey_df


def build_state_summary(amazon_df: pd.DataFrame) -> pd.DataFrame:
    state_summary = amazon_df.groupby("State").agg(
        total_spend=("Spend", "sum"),
        total_quantity=("Quantity", "sum"),
        order_count=("Spend", "count"),
        mean_price_unit=("Purchase Price Per Unit", "mean"),
    )
    spend_sum = amazon_df.groupby("State")["Spend"].sum()
    quantity_sum = amazon_df.groupby("State")["Quantity"].sum()
    state_summary["weighted_mean_price_unit"] = (
        (spend_sum / quantity_sum).reindex(state_summary.index)
    )
    category_spend = (
        amazon_df.groupby(["State", "Category"], dropna=False)
        .agg(spend=("Spend", "sum"))
        .reset_index()
    )
    category_spend = category_spend.merge(
        state_summary[["total_spend"]].reset_index(), on="State", how="left"
    )
    category_spend["share_of_spend"] = category_spend["spend"] / category_spend["total_spend"]
    category_spend["share_of_spend"] = category_spend["share_of_spend"].fillna(0)

    category_pivot = category_spend.pivot(
        index="State", columns="Category", values="share_of_spend"
    ).fillna(0)
    category_pivot.columns = [f"share_{c}" for c in category_pivot.columns]

    diversity = category_spend.groupby("State")["share_of_spend"].apply(
        lambda s: -np.sum(np.where(s > 0, s * np.log(s), 0))
    )
    state_summary["category_diversity"] = diversity.reindex(state_summary.index).fillna(0)

    def detect_category_group(category: str, keywords):
        return any(keyword in category for keyword in keywords)

    for group_name, keywords in CATEGORY_KEYWORDS.items():
        category_spend[group_name] = category_spend["Category"].apply(
            lambda category: any(k in category for k in keywords)
        )
        group_share = (
            category_spend[category_spend[group_name]]
            .groupby("State")["share_of_spend"]
            .sum()
        )
        state_summary[group_name + "_spend_share"] = group_share

    state_summary = state_summary.fillna(0)
    state_summary = state_summary.join(category_pivot, how="left").fillna(0)
    state_summary = state_summary.reset_index()
    return state_summary, category_spend


def analyze_survey_bias(survey_df: pd.DataFrame, acs_df: pd.DataFrame) -> pd.DataFrame:
    survey_state = (
        survey_df.groupby("State Abbrev")
        .agg(
            respondents=("Survey ResponseID", "count"),
            mean_income_estimate=("Income Band Approx", "mean"),
            median_income_estimate=("Income Band Approx", "median"),
        )
        .reset_index()
    )
    survey_state = survey_state[survey_state["State Abbrev"] != ""]
    survey_state = survey_state.merge(
        acs_df[["State", "median_household_income"]],
        left_on="State Abbrev",
        right_on="State",
        how="left",
    )
    survey_state["income_bias"] = (
        survey_state["mean_income_estimate"] - survey_state["median_household_income"]
    )
    return survey_state


def analyze_correlations(state_profile: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "median_household_income",
        "pct_bachelor_degree_or_higher",
        "pct_below_poverty_line",
        "pct_hispanic",
    ]
    summary = []
    min_state_coverage = 10
    for metric in metrics:
        for column in state_profile.columns:
            if column.startswith("share_") and np.issubdtype(state_profile[column].dtype, np.number):
                nonzero_count = state_profile[column].gt(0).sum()
                if nonzero_count < min_state_coverage:
                    continue
                subset = state_profile[[metric, column]].dropna()
                if len(subset) < min_state_coverage:
                    continue
                corr = subset.corr(method="pearson").iloc[0, 1]
                summary.append(
                    {
                        "metric": metric,
                        "category_share": column,
                        "pearson_corr": corr,
                        "state_coverage": nonzero_count,
                    }
                )
    result = pd.DataFrame(summary)
    if result.empty:
        return pd.DataFrame(
            columns=["metric", "category_share", "pearson_corr", "state_coverage"]
        )
    return result.sort_values("pearson_corr", ascending=False)


def run() -> None:
    print("Loading Amazon purchase data...")
    amazon_df = load_amazon_data()
    print(f"Loaded {len(amazon_df):,} Amazon purchase rows.")

    print("Loading survey data...")
    survey_df = load_survey_data()
    print(f"Loaded {len(survey_df):,} survey rows.")

    api_key = DEFAULT_CENSUS_API_KEY
    if not api_key or api_key.startswith("<"):
        raise RuntimeError(
            "Census API key is missing. Set CENSUS_API_KEY or update DEFAULT_CENSUS_API_KEY."
        )
    print("Fetching ACS data from Census API...")
    acs_df = fetch_census_data(api_key)
    print(f"Fetched ACS data for {len(acs_df):,} states.")
    acs_df.to_csv(ACS_CSV, index=False)
    print(f"Saved ACS profile to {ACS_CSV}")

    print("Aggregating Amazon state summary...")
    state_summary, category_spend = build_state_summary(amazon_df)
    state_summary.to_csv(MERGED_CSV, index=False)
    print(f"Saved Amazon state summary to {MERGED_CSV}")

    print("Joining Amazon and ACS state profiles...")
    state_profile = state_summary.merge(
        acs_df,
        left_on="State",
        right_on="State",
        how="left",
        validate="one_to_one",
    )
    state_profile.to_csv(DATA_DIR / "amazon_acs_merged.csv", index=False)
    print(f"Saved merged Amazon-ACS state profile to {DATA_DIR / 'amazon_acs_merged.csv'}")

    print("Analyzing survey representation bias...")
    survey_bias = analyze_survey_bias(survey_df, acs_df)
    survey_bias.to_csv(SURVEY_BIAS_CSV, index=False)
    print(f"Saved survey bias summary to {SURVEY_BIAS_CSV}")

    print("Computing category share outputs...")
    category_spend.to_csv(CATEGORY_SHARE_CSV, index=False)
    print(f"Saved category share by state to {CATEGORY_SHARE_CSV}")

    print("Computing correlation summary...")
    correlations = analyze_correlations(state_profile)
    correlations_path = DATA_DIR / "amazon_acs_correlation_summary.csv"
    correlations.to_csv(correlations_path, index=False)
    print(f"Saved correlation summary to {correlations_path}")

    print("Analysis complete.")
    print("Top 10 category correlations for income and demographic metrics:")
    print(correlations.head(10).to_string(index=False))


if __name__ == "__main__":
    run()
