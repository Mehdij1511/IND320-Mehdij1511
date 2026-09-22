from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components


DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	data["endring_fyllingsgrad_prosent"] = data["endring_fyllingsgrad"] * 100
	return data


st.title("Interactive plotting")
st.write("Explore changes in reservoir levels over time.")

data = load_data()

area_options = sorted(data["omrnr"].unique())
selected_area = st.selectbox("Reservoir area", area_options)

year_options = sorted(data["iso_aar"].unique(), reverse=True)
selected_year = st.selectbox("Year", year_options)

measure_options = {
	"Filling level (%)": "fyllingsgrad_prosent",
	"Filled amount (TWh)": "fylling_TWh",
	"Change from previous week (%)": "endring_fyllingsgrad_prosent",
}
selected_measure = st.selectbox("Measure", list(measure_options))

filtered_data = data[
	(data["omrnr"] == selected_area) & (data["iso_aar"] == selected_year)
].sort_values("dato_Id")

figure = px.line(
	filtered_data,
	x="dato_Id",
	y=measure_options[selected_measure],
	markers=True,
	labels={
		"dato_Id": "Date",
		measure_options[selected_measure]: selected_measure,
	},
	title=f"{selected_measure} - Area {selected_area}, {selected_year}",
)
figure.update_layout(
	height=600,
	hovermode="x unified",
	plot_bgcolor="#F2FBFA",
	margin={"l": 30, "r": 30, "t": 70, "b": 30},
)

plot_html = figure.to_html(include_plotlyjs=True, full_html=False)
components.html(plot_html, height=620, scrolling=False)
