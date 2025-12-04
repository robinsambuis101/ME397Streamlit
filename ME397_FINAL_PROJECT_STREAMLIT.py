#Final Project Streamlit App

import streamlit as st
import pandas as pd
import geopandas as gpd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import Point
import os
import sys

#first I'll do conditional data loading so the user just has to do it once

if os.path.exists("egrid_all_years.parquet"):
    df = pd.read_parquet("egrid_all_years.parquet")
    print("Necessary dataset already exists")
else:
    print("Downloading and processing individual eGRID files...")

    valid_years = [
        y for y in range(2004, 2024)
        if y not in [2017, 2015, 2013, 2011, 2008, 2006]
    ]

    year_file_dict = {
        2004: "eGRID2004_plant.xls",
        2005: "eGRID2005_plant.xls",
        2007: "eGRID2007_plant.xls",
        2009: "eGRID2009_data.xls",
        2010: "eGRID2010_Data.xls",
        2012: "eGRID2012_Data.xlsx",
        2014: "eGRID2014_data_metric_v2.xlsx",
        2016: "eGRID2016_data_metric_v2.xlsx",
        2018: "egrid2018_data_v2.xlsx",
        2019: "egrid2019_data.xlsx",
        2020: "eGRID2020_Data_v2.xlsx",
        2021: "eGRID2021_data.xlsx",
        2022: "egrid2022_data.xlsx",
        2023: "egrid2023_data_rev2.xlsx"
    }

    all_years = []
    for year in valid_years:
        print(f"Processing year {year}...")
        file_path = os.path.join("USeGRID", year_file_dict[year])
        sheet_name = "EGRDPLNT04" if year == 2004 else f"PLNT{str(year)[-2:]}"
        header_row = 4 if year <= 2012 else 1
        df_year = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)

        if "YEAR" not in df_year.columns:
            df_year["YEAR"] = year
        keep_cols = [
            "YEAR", "PSTATABB", "PNAME", "CNTYNAME", "LAT", "LON",
            "PLPRMFL", "PLNGENAN", "PLGENATN", "PLGENATR"
        ]
        df_clean = df_year[[c for c in keep_cols if c in df_year.columns]].copy()
        all_years.append(df_clean)

    df = pd.concat(all_years, ignore_index=True)
    df.to_parquet("egrid_all_years.parquet", index=False)
    print("Saved combined dataset.")

#now for the actual data manipulation

my_universal_path = Path("US_COUNTY_SHPFILE/US_county_cont.shp")
counties = gpd.read_file(my_universal_path) #crs 4326
state_to_abbrev = {   #full state names to abbreviations
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC"
}

year = st.selectbox("Select Year", sorted(df["YEAR"].unique()))
state = st.selectbox("Select State", sorted(state_to_abbrev.keys()))
state_abbrev = state_to_abbrev[state.lower()]
st.title(f"Energy Generation and Power Plants in {state.title()} in {year}")

df_state = df[(df["YEAR"] == year) & (df["PSTATABB"] == state_abbrev)]
if df_state.empty:
    st.error(f"No plant data found for {state.title()} in {year}.")
    st.stop()

geometry = [Point(xy) for xy in zip(df_state["LON"], df_state["LAT"])]
gdf_plants = gpd.GeoDataFrame(df_state, geometry=geometry, crs="EPSG:4326")

#geometry of the state
counties["STATE_NAME"] = counties["STATE_NAME"].str.lower()
state_shape = counties[counties["STATE_NAME"] == state].dissolve(by="STATE_NAME")
state_geojson = state_shape.__geo_interface__
center_lon = state_shape.geometry.centroid.x.values[0]
center_lat = state_shape.geometry.centroid.y.values[0]

# color mapping for fuel
fuel_types = gdf_plants["PLPRMFL"].unique()
color_map = px.colors.qualitative.Plotly
fuel_color_dict = {fuel: color_map[i % len(color_map)] for i, fuel in enumerate(fuel_types)}

fig_map = go.Figure()

#state map using scattermapbox
for i, fuel in enumerate(fuel_types):
    df_fuel = df_state[df_state["PLPRMFL"] == fuel]
    fig_map.add_trace(
        go.Scattermapbox(
            lat=df_fuel["LAT"],
            lon=df_fuel["LON"],
            mode="markers",
            marker=dict(size=10, color=fuel_color_dict[fuel]),
            name=fuel,
            text=[f"Plant: {p}<br>Fuel: {f}<br>Annual Generation: {g} MWh"
                  for p, f, g in zip(df_fuel["PNAME"], df_fuel["PLPRMFL"], df_fuel["PLNGENAN"])],
            hoverinfo="text",
            showlegend=True
        )
    )
#state map layout
fig_map.update_layout(
    mapbox_style="white-bg",
    mapbox_layers=[
        {"source": state_geojson, "type": "fill", "color": "lightgray", "opacity": 0.5},
        {"source": state_geojson, "type": "line", "color": "black", "line": {"width": 2}}],
    mapbox_center={"lat": center_lat, "lon": center_lon},
    mapbox_zoom=5,
    height=600,
    margin={"r":0,"t":0,"l":0,"b":0},
    showlegend=True
)
st.plotly_chart(fig_map, use_container_width=True)

#top 5 power plants
top5_plants = gdf_plants.nlargest(5, "PLNGENAN")
fig_top5 = go.Figure(
    go.Bar(
        x=top5_plants["PLNGENAN"][::-1],  # reverse for horizontal chart
        y=top5_plants["PNAME"][::-1],
        orientation="h",
        marker_color=[fuel_color_dict[f] for f in top5_plants["PLPRMFL"][::-1]],
        text=[f"{gen:.0f} MWh, {fuel}" for gen, fuel in zip(top5_plants["PLNGENAN"][::-1], top5_plants["PLPRMFL"][::-1])],
        textposition="auto"
    )
)
fig_top5.update_layout(title="Top 5 Power Plants by Annual Generation", xaxis_title="Total Generation (MWh)", yaxis_title="Plant Name", height=400)
st.plotly_chart(fig_top5, use_container_width=True)

#total generation in state
total_generation = gdf_plants["PLNGENAN"].sum()
st.write(f"**Total Generation in {state.title()}, {year}:** {total_generation:,.0f} MWh")

#bar chart
renewable_total = gdf_plants["PLGENATR"].sum()
nonrenewable_total = gdf_plants["PLGENATN"].sum()
renewable_pct = renewable_total / (renewable_total + nonrenewable_total) * 100
nonrenewable_pct = nonrenewable_total / (renewable_total + nonrenewable_total) * 100

fig_bar = go.Figure(go.Bar(
    x=["Nonrenewable", "Renewable"], y=[nonrenewable_total, renewable_total],
    marker_color=["gray", "green"], text=[f"{nonrenewable_pct:.1f}%", f"{renewable_pct:.1f}%"], textposition='auto'))
fig_bar.update_layout(title="Annual Generation: Renewable vs Nonrenewable", height=400, yaxis_title="Generation (MWh)")
st.plotly_chart(fig_bar, use_container_width=True)

#pie chart 
fuel_generation = (gdf_plants.groupby("PLPRMFL")[["PLGENATN", "PLGENATR"]].sum().sum(axis=1))
fuel_labels = fuel_generation.index.tolist()
fuel_values = fuel_generation.values.tolist()
fuel_colors = [fuel_color_dict[f] for f in fuel_labels]

fig_pie = go.Figure(go.Pie(labels=fuel_labels, values=fuel_values, marker_colors=fuel_colors))
fig_pie.update_layout(title="Fuel Mix of Power Plants", height=400)
st.plotly_chart(fig_pie, use_container_width=True)

#it's...beautiful