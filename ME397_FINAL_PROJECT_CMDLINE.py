#final project file that takes user input instead of creating a streamlit app

import pandas as pd
import geopandas as gpd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from shapely.geometry import Point
from plotly.offline import plot
import webbrowser
import os
import sys

if len(sys.argv) != 3:
    print('Use as: python ME397_FINAL_PROJECT.py YEAR STATE')
    sys.exit(1)
#input handling
year = int(sys.argv[1].strip())
state = sys.argv[2].strip().lower()

#input year/state fail safes
if year < 2004 or year > 2023:
    print("Error: year must be between 2004 and 2023.")
    sys.exit(1)
if year in [2017, 2015, 2013, 2011, 2008, 2006]:
    print(f"eGRID data for {year} is not available.")
    sys.exit(1)

my_universal_path = Path("US_COUNTY_SHPFILE/US_county_cont.shp")
counties = gpd.read_file(my_universal_path) #crs 4326
contiguous_states = set(counties["STATE_NAME"].unique())
contiguous_states_lower = {s.lower() for s in contiguous_states}

if state not in contiguous_states_lower:
    print(f"{state.title()} is not a state in the contiguous US!")
    sys.exit(1)

#now read in the proper excel sheet
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

if year == 2004:
    sheet_name = "EGRDPLNT04"
else:
    sheet_name = f"PLNT{str(year)[-2:]}"

if year <= 2012:
    header_row = 4
else:
    header_row = 1
# all different excel names and sheet names and formats have been taken care of, now read in data
file_path = os.path.join("USeGRID", year_file_dict[year])
df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)

#we want to stick with YEAR PSTATABB PNAME CNTYNAME LAT LON PLPRMFL PLNGENAN PLGENATN PLGENATR

if "YEAR" not in df.columns:
    df["YEAR"] = year
    if f"SEQPLT{str(year)[-2:]}" in df.columns and "PSTATABB" in df.columns:
        cols = df.columns.tolist()
        insert_loc = cols.index(f"SEQPLT{str(year)[-2:]}") + 1  # insert after SEQPLTXX
        # put YEAR in desired position
        cols.insert(insert_loc, cols.pop(cols.index("YEAR")))
        df = df[cols]

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

df_state = df[df["PSTATABB"] == state_to_abbrev[state]]
df_state = df_state[["YEAR", "PSTATABB", "PNAME", "CNTYNAME", "LAT", "LON", 
                     "PLPRMFL", "PLNGENAN", "PLGENATN", "PLGENATR"]]

counties["STATE_NAME"] = counties["STATE_NAME"].str.lower()
state_shape = counties[counties["STATE_NAME"] == state].dissolve(by="STATE_NAME")
# state_shape.plot() to show state, EPSG 4326

#need to convert df_state to geodataframe
geometry = [Point(xy) for xy in zip(df_state["LON"], df_state["LAT"])]
gdf_plants = gpd.GeoDataFrame(df_state, geometry=geometry, crs="EPSG:4326")

counties["STATE_NAME"] = counties["STATE_NAME"].str.lower()
state_shape = counties[counties["STATE_NAME"] == state].dissolve()
state_geojson = state_shape.__geo_interface__
center_lon = state_shape.geometry.centroid.x.values[0]
center_lat = state_shape.geometry.centroid.y.values[0]

fuel_types = gdf_plants["PLPRMFL"].unique()
color_map = px.colors.qualitative.Plotly
fuel_color_dict = {fuel: color_map[i % len(color_map)] for i, fuel in enumerate(fuel_types)}


# state map creation
fig_map = go.Figure()
for fuel in fuel_types:
    df_fuel = df_state[df_state["PLPRMFL"] == fuel]
    fig_map.add_trace(
        go.Scattermapbox(
            lat=df_fuel["LAT"],
            lon=df_fuel["LON"],
            mode="markers",
            marker=dict(size=10, color=fuel_color_dict[fuel]),
            name=fuel,
            text=[
                f"Plant: {p}<br>Fuel: {f}<br>Annual Generation: {g} MWh"
                for p, f, g in zip(df_fuel["PNAME"], df_fuel["PLPRMFL"], df_fuel["PLNGENAN"])
            ],
            hoverinfo="text"
        )
    )
fig_map.update_layout(
    title=f"State Map of All Power Plants in {state.title()} in {year}",
    mapbox_style="white-bg",
    mapbox_layers=[
        {"source": state_geojson, "type": "fill", "color": "lightgray", "opacity": 0.5},
        {"source": state_geojson, "type": "line", "color": "black", "line": {"width": 2}}
    ],
    mapbox_center={"lat": center_lat, "lon": center_lon},
    mapbox_zoom=5,
    height=600
)

#top 5 plants by generation
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

# bar chart of renewables to non
renewable_total = gdf_plants["PLGENATR"].sum()
nonrenewable_total = gdf_plants["PLGENATN"].sum()
renewable_pct = renewable_total / (renewable_total + nonrenewable_total) * 100
nonrenewable_pct = nonrenewable_total / (renewable_total + nonrenewable_total) * 100

fig_bar = go.Figure(
    go.Bar(
        x=["Nonrenewable", "Renewable"],
        y=[nonrenewable_total, renewable_total],
        marker_color=["gray", "green"],
        text=[f"{nonrenewable_pct:.1f}%", f"{renewable_pct:.1f}%"],
        textposition="auto"
    )
)
fig_bar.update_layout(title="Bar Chart Showing Renewable vs Nonrenewable Generation", yaxis_title="Generation (MWh)", height=400)
total_generation = gdf_plants["PLNGENAN"].sum()
fig_bar.add_annotation(
    text=f"Total Generation in {state.title()}, {year}: {total_generation:,.1f} MWh",
    xref="paper", yref="paper",
    x=0.5, y=1.15,
    showarrow=False,
    font=dict(size=14, color="black"),
    align="center"
)
# pie chart of fuel types
fuel_generation = gdf_plants.groupby("PLPRMFL")[["PLGENATN", "PLGENATR"]].sum().sum(axis=1)
fuel_labels = fuel_generation.index.tolist()
fuel_values = fuel_generation.values.tolist()
fuel_colors = [fuel_color_dict[f] for f in fuel_labels]

fig_pie = go.Figure(go.Pie(labels=fuel_labels, values=fuel_values, marker_colors=fuel_colors))
fig_pie.update_layout(title="Pie Chart Showing Fuel Mix of Power Plants", height=400)

# now combine all charts into a single html file
html_content = ""
for fig in [fig_map, fig_top5, fig_bar, fig_pie]:
    html_content += plot(fig, include_plotlyjs='cdn', output_type='div')
with open("power_plant_dashboard.html", "w") as f:
    f.write(f"<html><head><title>{state.title()} Power Plants {year}</title></head><body>{html_content}</body></html>")

webbrowser.open("power_plant_dashboard.html")