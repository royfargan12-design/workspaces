import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------- App config ----------------
st.set_page_config(page_title="GDP Explorer (2020–2025)", layout="wide")

# ---------------- Helpers ----------------
@st.cache_data
def load_csv(path_or_buffer):
    df = pd.read_csv(path_or_buffer)
    # Ensure numeric year cols
    if "Country" not in df.columns:
        raise ValueError("CSV must include a 'Country' column.")
    year_cols = [c for c in df.columns if c != "Country"]
    for c in year_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def get_year_cols(df):
    return sorted([c for c in df.columns if c != "Country"], key=lambda x: int(x))

def latest_value(row, year_cols):
    for y in sorted(year_cols, key=int, reverse=True):
        if pd.notna(row[y]):
            return row[y], y
    return np.nan, np.nan

def pct_change(a, b):
    if pd.isna(a) or pd.isna(b) or a == 0:
        return np.nan
    return (b - a) / a * 100.0

def cagr(a, b, n_years):
    if pd.isna(a) or pd.isna(b) or a <= 0 or n_years <= 0:
        return np.nan
    return ((b / a) ** (1.0 / n_years) - 1.0) * 100.0

def to_long(df, year_cols):
    long_df = df[["Country"] + year_cols].melt(
        id_vars="Country", var_name="Year", value_name="GDP"
    )
    long_df["Year"] = pd.to_numeric(long_df["Year"], errors="coerce")
    return long_df

def annual_growth_series(row):
    ys = [int(y) for y in get_year_cols(row.to_frame().T)]
    vals = [row.get(str(y), np.nan) for y in ys]
    growth = []
    for i in range(1, len(vals)):
        a, b = vals[i-1], vals[i]
        if pd.notna(a) and pd.notna(b) and a > 0:
            growth.append((b - a) / a * 100.0)
    return growth

# ---------------- Sidebar: data input ----------------
st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload CSV (Country, 2020..2025)", type=["csv"])
default_path = "2020-2025.csv"  # optional: put your file in the repo root with this name

df = None
if uploaded is not None:
    df = load_csv(uploaded)
else:
    try:
        df = load_csv(default_path)
        st.sidebar.info(f"Using default file: {default_path}")
    except Exception:
        st.sidebar.warning("No file uploaded and default file not found. Please upload a CSV.")
        df = pd.DataFrame(columns=["Country","2020","2021","2022","2023","2024","2025"])

if df.empty or "Country" not in df.columns:
    st.stop()

year_cols = get_year_cols(df)

# Enrich with latest snapshot + metrics
latest = df.apply(lambda r: latest_value(r, year_cols), axis=1, result_type="expand")
df["LatestGDP"] = latest[0]
df["LatestYear"] = latest[1]
df["Pct_2020_2021"] = df.apply(lambda r: pct_change(r.get("2020"), r.get("2021")), axis=1) if set(["2020","2021"]).issubset(df.columns) else np.nan
df["Pct_2020_2022"] = df.apply(lambda r: pct_change(r.get("2020"), r.get("2022")), axis=1) if set(["2020","2022"]).issubset(df.columns) else np.nan
df["CAGR_2020_2025"] = df.apply(lambda r: cagr(r.get("2020"), r.get("2025"), 5), axis=1) if set(["2020","2025"]).issubset(df.columns) else np.nan

# ---------------- Header & KPIs ----------------
st.title("GDP Explorer (2020–2025)")
top_n = st.sidebar.slider("Top-N major economies (by latest GDP)", 10, 40, 20, 5)

n_countries = int(df["Country"].nunique())
common_latest_year = (df["LatestYear"].mode().iat[0] if df["LatestYear"].dropna().size else "—")
if df["LatestGDP"].dropna().size:
    top_row = df.loc[df["LatestGDP"].idxmax()]
    top_country = str(top_row["Country"]); top_gdp_year = str(top_row["LatestYear"])
    top_gdp_val = float(top_row["LatestGDP"])
else:
    top_country, top_gdp_year, top_gdp_val = "—", "—", float("nan")

highest_cagr = df["CAGR_2020_2025"].max(skipna=True) if "CAGR_2020_2025" in df else np.nan
highest_cagr_country = (df.sort_values("CAGR_2020_2025", ascending=False)["Country"].iat[0]
                        if df["CAGR_2020_2025"].dropna().size else "—")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Countries", f"{n_countries:,}")
c2.metric("Most common latest year", f"{common_latest_year}")
c3.metric("Top by latest GDP", f"{top_country}", help=f"Year: {top_gdp_year}, Value: {top_gdp_val:,.0f}")
c4.metric("Highest CAGR (2020–2025)", f"{highest_cagr_country}",
          help=(f"{highest_cagr:.2f}%" if pd.notna(highest_cagr) else "—"))

# ---------------- Tabs ----------------
tab_overview, tab_map, tab_compare, tab_surprise, tab_table = st.tabs(
    ["Overview", "World Map", "Compare Countries", "Surprising Growers", "Data Table"]
)

# ===== Overview =====
with tab_overview:
    st.subheader("Preview")
    st.dataframe(df[["Country"] + year_cols].head(30), use_container_width=True)

    st.subheader("Major economies: 2020→2021 impact")
    majors = df.nlargest(top_n, "LatestGDP").copy()
    bar_data = majors[["Country","Pct_2020_2021"]].dropna().sort_values("Pct_2020_2021", ascending=False)
    if not bar_data.empty:
        fig_bar = px.bar(bar_data, x="Pct_2020_2021", y="Country",
                         orientation="h", labels={"Pct_2020_2021":"% change 2020→2021","Country":"Country"},
                         title="Immediate pandemic hit/rebound (Top-N by latest GDP)")
        fig_bar.update_layout(yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Need both 2020 and 2021 columns with values to show this chart.")

# ===== World Map =====
with tab_map:
    st.subheader("Choropleth map")
    # Choose a year present in the file
    y_min, y_max = int(min(map(int, year_cols))), int(max(map(int, year_cols)))
    map_year = st.slider("Map year", min_value=y_min, max_value=y_max, value=min(max(2021, y_min), y_max))
    map_year_str = str(map_year)

    if map_year_str in df.columns:
        map_df = df[["Country", map_year_str]].dropna()
        if not map_df.empty:
            fig_map = px.choropleth(
                map_df,
                locations="Country",
                locationmode="country names",
                color=map_year_str,
                hover_name="Country",
                title=f"GDP in {map_year}",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info(f"No data for {map_year}.")
    else:
        st.warning(f"Column '{map_year_str}' not found in the CSV.")

# ===== Compare Countries =====
with tab_compare:
    st.subheader("Compare countries over time")
    options = sorted(df["Country"].dropna().unique().tolist())
    selected = st.multiselect("Select countries", options[:100], default=options[:6] if len(options) >= 6 else options)

    if selected:
        long_df = to_long(df[df["Country"].isin(selected)], year_cols).dropna()
        if not long_df.empty:
            fig_line = px.line(long_df, x="Year", y="GDP", color="Country", markers=True, title="GDP trajectories")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No valid values to plot.")
    else:
        st.info("Pick at least one country to compare.")

# ===== Surprising Growers =====
with tab_surprise:
    st.subheader("Surprising growers: CAGR vs Volatility")
    base_top_n = st.number_input("Exclude Top-N by 2020 GDP", min_value=10, max_value=60, value=20, step=5)

    has_2020_2025 = set(["2020","2025"]).issubset(df.columns)
    if has_2020_2025:
        df["Has_2020_and_2025"] = df[["2020","2025"]].notna().all(axis=1)
        top_base = set(df.nlargest(base_top_n, "2020")["Country"].tolist())
        candidates = df[(~df["Country"].isin(top_base)) & (df["Has_2020_and_2025"])].copy()

        valid_cagrs = candidates["CAGR_2020_2025"].dropna()
        if valid_cagrs.size:
            percentile = st.slider("CAGR percentile threshold", 50, 99, 90, 1)
            threshold = np.nanpercentile(valid_cagrs, percentile)
            surprising = candidates[candidates["CAGR_2020_2025"] >= threshold].copy()

            # volatility
            def series_growth(row):
                vals = [row.get(str(y), np.nan) for y in map(int, year_cols)]
                growth = []
                for i in range(1, len(vals)):
                    a, b = vals[i-1], vals[i]
                    if pd.notna(a) and pd.notna(b) and a > 0:
                        growth.append((b - a) / a * 100.0)
                return growth

            surprising["Volatility_SD"] = surprising.apply(
                lambda r: np.std(series_growth(r)) if len(series_growth(r))>0 else np.nan, axis=1)
            surprising["Avg_Annual_Growth"] = surprising.apply(
                lambda r: np.nanmean(series_growth(r)) if len(series_growth(r))>0 else np.nan, axis=1)

            view = surprising[["Country","2020","2025","CAGR_2020_2025","Avg_Annual_Growth","Volatility_SD"]]\
                   .sort_values("CAGR_2020_2025", ascending=False).round(2)
            st.dataframe(view, use_container_width=True)

            if not view.empty:
                fig_sc = px.scatter(view, x="Volatility_SD", y="CAGR_2020_2025", text="Country",
                                    labels={"Volatility_SD":"Volatility (SD of annual % change)",
                                            "CAGR_2020_2025":"CAGR % (2020–2025)"},
                                    title="Risk–Return view")
                fig_sc.update_traces(textposition="top center")
                st.plotly_chart(fig_sc, use_container_width=True)
        else:
            st.info("Not enough CAGR data to compute percentile threshold.")
    else:
        st.info("Need both 2020 and 2025 columns to compute CAGR-based surprises.")

# ===== Data Table (search & filters) =====
with tab_table:
    st.subheader("Data table with search & filters")
    long_df_all = to_long(df, year_cols).dropna()

    q = st.text_input("Search country (case-insensitive)", value="")
    y_min, y_max = int(long_df_all["Year"].min()), int(long_df_all["Year"].max())
    year_range = st.slider("Year range", min_value=y_min, max_value=y_max, value=(y_min, y_max))
    v_min, v_max = float(long_df_all["GDP"].min()), float(long_df_all["GDP"].max())
    value_range = st.slider("GDP range", min_value=float(v_min), max_value=float(v_max), value=(float(v_min), float(v_max)))

    tbl = long_df_all.copy()
    if q:
        tbl = tbl[tbl["Country"].str.contains(q, case=False, na=False)]
    tbl = tbl[(tbl["Year"] >= year_range[0]) & (tbl["Year"] <= year_range[1])]
    tbl = tbl[(tbl["GDP"] >= value_range[0]) & (tbl["GDP"] <= value_range[1])]

    st.dataframe(tbl.sort_values(["Country","Year"]).reset_index(drop=True), use_container_width=True, height=380)

    st.markdown("**Download filtered CSV**")
    st.download_button("Download CSV", tbl.to_csv(index=False).encode("utf-8"), "filtered_gdp.csv", "text/csv")

st.caption("Tip: for GDP per capita, add a population CSV (Country, 2020..2025) and divide on the fly.")
