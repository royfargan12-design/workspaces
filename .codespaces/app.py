import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Global Dashboard", layout="wide")

# --- demo data ---
countries = ["USA", "Germany", "India", "Brazil", "Japan", "Israel", "UK", "France", "Canada", "Australia"]
data = pd.DataFrame({
    "country": np.random.choice(countries, 300),
    "year": np.random.choice(range(2015, 2025), 300),
    "value": np.random.randint(50, 500, 300)
})

# ===================== KPIs =====================
st.markdown("### 🌍 Global KPIs")
col1, col2, col3 = st.columns(3)
col1.metric("Total Countries", data["country"].nunique())
col2.metric("Avg Value", round(data["value"].mean(), 2))
col3.metric("Max Value", int(data["value"].max()))

# ===================== World Map =====================
st.markdown("### 🗺️ World Map")
map_year = st.slider("Map year", min_value=int(data["year"].min()), max_value=int(data["year"].max()), value=2021)
map_df = data[data["year"] == map_year].groupby("country", as_index=False)["value"].mean()
fig_map = px.choropleth(map_df, locations="country", locationmode="country names",
                        color="value", color_continuous_scale="Blues",
                        title=f"Average Value per Country — {map_year}")
st.plotly_chart(fig_map, use_container_width=True)

# ===================== Comparison =====================
st.markdown("### 📈 Country Comparison")
sel = st.multiselect("Select countries", sorted(data["country"].unique().tolist()), default=["USA", "India"])
if sel:
    comp = data[data["country"].isin(sel)]
    fig_line = px.line(comp, x="year", y="value", color="country", markers=True, title="Trends")
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Pick at least one country.")

# ===================== Surprising Growers =====================
st.markdown("### 🚀 Surprising Growers")
g = data.groupby(["country", "year"])["value"].mean().reset_index()
pivot = g.pivot(index="year", columns="country", values="value").sort_index().fillna(method="ffill").fillna(0)
growth_rate = pivot.pct_change().mean().sort_values(ascending=False).reset_index()
growth_rate.columns = ["country", "avg_growth"]
fig_scatter = px.scatter(growth_rate, x="country", y="avg_growth", size="avg_growth",
                         color="avg_growth", color_continuous_scale="Viridis",
                         title="Average Growth Rate by Country")
st.plotly_chart(fig_scatter, use_container_width=True)

# ===================== Data Table with filters =====================
st.markdown("### 🔎 Data Table (search & filters)")

# search
q = st.text_input("Search country (case-insensitive)", value="")

# year filter
y_min, y_max = int(data["year"].min()), int(data["year"].max())
year_range = st.slider("Year range", min_value=y_min, max_value=y_max, value=(y_min, y_max))

# value filter
v_min, v_max = int(data["value"].min()), int(data["value"].max())
value_range = st.slider("Value range", min_value=v_min, max_value=v_max, value=(v_min, v_max))

tbl = data.copy()
if q:
    tbl = tbl[tbl["country"].str.contains(q, case=False, na=False)]
tbl = tbl[(tbl["year"] >= year_range[0]) & (tbl["year"] <= year_range[1])]
tbl = tbl[(tbl["value"] >= value_range[0]) & (tbl["value"] <= value_range[1])]

st.dataframe(tbl.sort_values(["country", "year"]).reset_index(drop=True), use_container_width=True, height=360)

# download filtered
st.markdown("### 📥 Download")
csv = tbl.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered CSV", csv, "filtered_data.csv", "text/csv")
