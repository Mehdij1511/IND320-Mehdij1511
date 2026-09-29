from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	return data


st.title("Reservoir snapshot")
st.write("A quick view of reservoir conditions across Norway.")

data = load_data()
year_options = sorted(data["iso_aar"].unique(), reverse=True)
selected_year = st.selectbox("Year", year_options)
year_data = data[data["iso_aar"] == selected_year]

latest_date = year_data["dato_Id"].max()
latest_data = year_data[year_data["dato_Id"] == latest_date]
average_filling = latest_data["fyllingsgrad_prosent"].mean()
total_capacity = latest_data["kapasitet_TWh"].sum()
total_filled = latest_data["fylling_TWh"].sum()

metric_one, metric_two, metric_three = st.columns(3)
metric_one.metric("Average filling", f"{average_filling:.1f}%")
metric_two.metric("Total capacity", f"{total_capacity:.1f} TWh")
metric_three.metric("Filled volume", f"{total_filled:.1f} TWh")
st.caption(f"Latest observation in {selected_year}: {latest_date:%d %B %Y}")

area_summary = (
	latest_data.groupby("omrnr", as_index=False)["fyllingsgrad_prosent"]
	.mean()
	.sort_values("fyllingsgrad_prosent", ascending=False)
)

figure = px.bar(
	area_summary,
	x="omrnr",
	y="fyllingsgrad_prosent",
	text_auto=".1f",
	labels={"omrnr": "Reservoir area", "fyllingsgrad_prosent": "Filling level (%)"},
	title="Filling level by reservoir area",
)
figure.update_layout(
	height=500,
	plot_bgcolor="#F2FBFA",
	margin={"l": 30, "r": 30, "t": 70, "b": 30},
)
st.plotly_chart(figure, use_container_width=True)
