"""Prepare and summarize World Bank Nigeria market-level food price estimates."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "NGA_RTFP_mkt_2007_2026-08-24.csv"
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

# These six staple groups form the core dashboard. Prices are compared over time
# within each product; source units differ between products (see product_dimension).
STAPLES = ["beans", "gari_fao", "maize_fao", "rice_fao", "sorghum_fao", "yam"]
DISPLAY = {
    "beans": "Beans",
    "gari_fao": "Gari",
    "maize_fao": "Maize",
    "rice_fao": "Rice",
    "sorghum_fao": "Sorghum",
    "yam": "Yam",
}


def read_source() -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(f"Place the World Bank source CSV at: {RAW}")
    df = pd.read_csv(RAW, low_memory=False)
    required = {"ISO3", "country", "adm1_name", "adm2_name", "mkt_name", "geo_id", "price_date", "currency", "components"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required source fields: {sorted(missing)}")
    df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce")
    df = df.loc[df["ISO3"].eq("NGA")].copy()
    if df["price_date"].isna().any():
        raise ValueError("Some source dates could not be parsed")
    dupes = int(df.duplicated(["geo_id", "price_date"]).sum())
    if dupes:
        raise ValueError(f"Found {dupes} duplicate market-month records")
    return df


def parse_source_units(components: str) -> dict[str, str]:
    if not isinstance(components, str):
        return {}
    return {name.strip(): unit.strip() for name, unit in re.findall(r"(?:^|, )([a-z0-9_]+) \(([^,]+), Index Weight", components)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    source_df = read_source()
    aggregate_labels = {"Geopolitical Zone", "National Average", "Market Average"}
    aggregate_mask = source_df["adm1_name"].isin(aggregate_labels)
    aggregate_ids = source_df.loc[aggregate_mask, ["geo_id", "adm1_name", "adm2_name", "mkt_name"]].drop_duplicates()
    df = source_df.loc[~aggregate_mask].copy()
    # Correct a source spelling variant for grouping while retaining the original label.
    df["source_adm1_name"] = df["adm1_name"]
    df["adm1_name"] = df["adm1_name"].replace({"Kano State (1)": "Kano"})

    all_price_cols = [c for c in df.columns if c.startswith("c_") and c != "c_food_price_index"]
    missing_staples = [p for p in STAPLES if f"c_{p}" not in df.columns]
    if missing_staples:
        raise ValueError(f"Missing selected close-estimate fields: {missing_staples}")
    products = STAPLES
    unit_map = parse_source_units(df["components"].dropna().iloc[0])

    product_rows = []
    for code in products:
        product_rows.append({
            "commodity_code": code,
            "commodity_name": DISPLAY.get(code, code.replace("_", " ").title()),
            "source_unit": unit_map.get(code, "See source components field"),
        })
    product_dim = pd.DataFrame(product_rows)
    product_dim.to_csv(OUT / "dim_commodity.csv", index=False)

    market_cols = ["geo_id", "ISO3", "country", "adm1_name", "source_adm1_name", "adm2_name", "mkt_name", "lat", "lon"]
    market_dim = df[market_cols].drop_duplicates("geo_id").rename(columns={
        "geo_id": "market_id", "ISO3": "country_code", "country": "country_name", "adm1_name": "state_name", "source_adm1_name": "source_state_label", "adm2_name": "local_government_area",
        "mkt_name": "market_name", "lat": "latitude", "lon": "longitude",
    })
    market_dim.to_csv(OUT / "dim_market.csv", index=False)
    aggregate_ids.to_csv(REPORTS / "excluded_summary_geographies.csv", index=False)

    base_cols = ["geo_id", "price_date", "currency", "spatially_interpolated"]
    product_frames = []
    for code in products:
        frame = df[base_cols].copy()
        frame["commodity_code"] = code
        frame["commodity_name"] = DISPLAY[code]
        frame["source_unit"] = unit_map.get(code, "See source components field")
        frame["estimated_price"] = pd.to_numeric(df[f"c_{code}"], errors="coerce").to_numpy()
        frame["trust_score"] = pd.to_numeric(df[f"trust_{code}"], errors="coerce").to_numpy()
        product_frames.append(frame)
    melt = pd.concat(product_frames, ignore_index=True).rename(columns={"geo_id": "market_id"})
    melt["year"] = melt["price_date"].dt.year.astype("int16")
    melt["month"] = melt["price_date"].dt.month.astype("int8")
    tidy_cols = [
        "price_date", "year", "month", "market_id", "commodity_code", "commodity_name", "source_unit", "estimated_price", "currency",
        "trust_score", "spatially_interpolated",
    ]
    tidy = melt[tidy_cols].merge(market_dim[["market_id", "state_name", "local_government_area", "market_name", "latitude", "longitude"]], on="market_id", how="left", validate="many_to_one")
    tidy = tidy[tidy["commodity_code"].isin(STAPLES)].copy()
    tidy = tidy.sort_values(["price_date", "state_name", "market_name", "commodity_code"])
    tidy.to_csv(OUT / "fact_staple_market_month.csv", index=False, date_format="%Y-%m-%d")

    # Equal-weighted means summarize observed market estimates; they are not
    # population-weighted consumer prices or an official national CPI series.
    monthly = tidy.groupby(["price_date", "commodity_code", "commodity_name", "source_unit", "currency"], as_index=False).agg(
        market_count=("market_id", "nunique"),
        mean_estimated_price=("estimated_price", "mean"),
        median_estimated_price=("estimated_price", "median"),
        mean_trust_score=("trust_score", "mean"),
        interpolated_market_share=("spatially_interpolated", "mean"),
    )
    monthly = monthly.sort_values(["commodity_code", "price_date"])
    monthly["mom_change_pct"] = monthly.groupby("commodity_code")["mean_estimated_price"].pct_change(fill_method=None) * 100
    monthly["yoy_change_pct"] = monthly.groupby("commodity_code")["mean_estimated_price"].pct_change(periods=12, fill_method=None) * 100
    monthly.to_csv(OUT / "agg_national_monthly.csv", index=False, date_format="%Y-%m-%d")

    state = tidy.groupby(["price_date", "state_name", "commodity_code", "commodity_name", "source_unit", "currency"], as_index=False).agg(
        market_count=("market_id", "nunique"),
        mean_estimated_price=("estimated_price", "mean"),
        median_estimated_price=("estimated_price", "median"),
        mean_trust_score=("trust_score", "mean"),
        interpolated_market_share=("spatially_interpolated", "mean"),
    )
    state = state.sort_values(["state_name", "commodity_code", "price_date"])
    state["yoy_change_pct"] = state.groupby(["state_name", "commodity_code"])["mean_estimated_price"].pct_change(periods=12, fill_method=None) * 100
    state.to_csv(OUT / "agg_state_monthly.csv", index=False, date_format="%Y-%m-%d")

    all_dates = df["price_date"].dropna()
    source_price = df[all_price_cols].apply(pd.to_numeric, errors="coerce")
    qa = {
        "source_file": RAW.name,
        "source_rows": int(len(df)),
        "raw_source_rows_including_aggregates": int(len(source_df)),
        "source_columns": int(source_df.shape[1]),
        "country_values": sorted(df["country"].dropna().unique().tolist()),
        "currency_values": sorted(df["currency"].dropna().unique().tolist()),
        "source_date_min": all_dates.min().strftime("%Y-%m-%d"),
        "source_date_max": all_dates.max().strftime("%Y-%m-%d"),
        "distinct_market_ids_in_file": int(df["geo_id"].nunique()),
        "distinct_source_geo_ids_including_aggregates": int(source_df["geo_id"].nunique()),
        "excluded_aggregate_geo_ids": int(aggregate_ids["geo_id"].nunique()),
        "excluded_aggregate_rows": int(aggregate_mask.sum()),
        "excluded_aggregate_labels": sorted(aggregate_ids["adm1_name"].unique().tolist()),
        "distinct_states_in_file": int(df["adm1_name"].nunique()),
        "duplicate_market_month_rows": int(df.duplicated(["geo_id", "price_date"]).sum()),
        "missing_market_id_rows": int(df["geo_id"].isna().sum()),
        "negative_close_estimates": int((source_price < 0).sum().sum()),
        "missing_close_estimates": {c: int(source_price[c].isna().sum()) for c in all_price_cols},
        "core_staple_products": STAPLES,
        "core_staple_rows_after_reshape": int(len(tidy)),
        "source_count_note": "The raw file has 74 geo_id values, including 7 summary geography IDs (Geopolitical Zone, National Average, Market Average). These were excluded to retain physical market rows only; the catalog reports 73 markets, while 67 distinct local market IDs remain after exclusions.",
        "state_label_note": "The source label Kano State (1) is normalized to Kano for analysis; the original spelling is retained in dim_market.csv.",
        "aggregation_note": "National and state monthly summaries are equal-weighted means of physical market estimates; they are not population-weighted or official CPI statistics.",
    }
    (REPORTS / "data_quality_summary.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    latest = monthly.loc[monthly["price_date"].eq(monthly["price_date"].max())].sort_values("yoy_change_pct", ascending=False)
    latest.to_csv(REPORTS / "latest_month_summary.csv", index=False, date_format="%Y-%m-%d")
    latest_states = state.loc[state["price_date"].eq(state["price_date"].max())].sort_values(["commodity_code", "mean_estimated_price"])
    latest_states.to_csv(REPORTS / "latest_state_summary.csv", index=False, date_format="%Y-%m-%d")

    # A within-product index makes long-run trajectories readable without
    # implying that differently sized source units are directly comparable.
    colors = {"beans": "#136f63", "gari_fao": "#e07a1f", "maize_fao": "#4472c4", "rice_fao": "#9b59b6", "sorghum_fao": "#c0392b", "yam": "#708090"}
    indexed = monthly.copy()
    indexed["index_2007_01_100"] = indexed["mean_estimated_price"] / indexed.groupby("commodity_code")["mean_estimated_price"].transform("first") * 100
    width, height = 1120, 650
    left, right, top, bottom = 90, 35, 105, 90
    plot_w, plot_h = width-left-right, height-top-bottom
    ymax = max(500, int(((indexed["index_2007_01_100"].max() // 500) + 1) * 500))
    xmin, xmax = indexed["price_date"].min(), indexed["price_date"].max()
    def px(date: pd.Timestamp) -> float:
        return left + (date-xmin).days / max(1, (xmax-xmin).days) * plot_w
    def py(value: float) -> float:
        return top + plot_h - value / ymax * plot_h
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#243247}.grid{stroke:#e5e9ef;stroke-width:1}.axis{stroke:#718096;stroke-width:1.2}</style>',
           '<text x="90" y="38" font-size="25" font-weight="700">Modeled staple price estimates over time</text>',
           '<text x="90" y="66" font-size="15" fill="#536273">Index: each product’s equal-weighted market mean, January 2007 = 100</text>',
           '<text x="90" y="88" font-size="12" fill="#536273">Close-estimate series; source units differ. Lines show within-product movement, not comparable price levels.</text>']
    for tick in range(0, ymax+1, max(100, ymax//6)):
        y = py(tick)
        svg.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>')
        svg.append(f'<text x="{left-12}" y="{y+4:.1f}" font-size="12" text-anchor="end">{tick:,}</text>')
    svg.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/><line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>')
    for yr in range(xmin.year, xmax.year+1):
        if (yr-xmin.year) % 2 == 0 or yr == xmax.year:
            dt = pd.Timestamp(year=yr, month=1, day=1)
            if dt > xmax: continue
            x = px(dt)
            svg.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}"/>')
            svg.append(f'<text x="{x:.1f}" y="{height-bottom+24}" font-size="12" text-anchor="middle">{yr}</text>')
    for code in STAPLES:
        series = indexed.loc[indexed["commodity_code"].eq(code)].sort_values("price_date")
        pts = " ".join(f'{px(row.price_date):.1f},{py(row.index_2007_01_100):.1f}' for row in series.itertuples())
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{colors[code]}" stroke-width="2.7" stroke-linejoin="round" stroke-linecap="round"/>')
    legend = list(zip(STAPLES, [DISPLAY[c] for c in STAPLES]))
    for i, (code, label) in enumerate(legend):
        x = left + (i%3)*290
        y = height-35 + (i//3)*23
        svg.append(f'<line x1="{x}" y1="{y-4}" x2="{x+22}" y2="{y-4}" stroke="{colors[code]}" stroke-width="3"/><text x="{x+30}" y="{y}" font-size="13">{label}</text>')
    svg.append('</svg>')
    (REPORTS / "staple_price_index.svg").write_text("\n".join(svg), encoding="utf-8")

    print(json.dumps(qa, indent=2))
    print("\nLatest month national estimates and year-over-year change:")
    print(latest[["commodity_name", "mean_estimated_price", "yoy_change_pct", "market_count"]].to_string(index=False))


if __name__ == "__main__":
    main()
