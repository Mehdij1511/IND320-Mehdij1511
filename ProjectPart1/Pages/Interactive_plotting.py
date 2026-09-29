from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Locate the dataset relative to this file so the app works from the project root.
DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	"""Load the reservoir data and add percentage-based display columns."""
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])

	# Convert decimal values to percentages for easier interpretation.
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	data["endring_fyllingsgrad_prosent"] = data["endring_fyllingsgrad"] * 100
	return data

# Add a title and description for the interactive plotting page.
st.title("Interactive plotting")
st.write("Explore changes in reservoir levels over time.")

# Load the data using Streamlit caching to avoid reading the file repeatedly.
data = load_data()

# Create selection widgets for the user to filter the data.
area_options = sorted(data["omrnr"].unique())
selected_area = st.selectbox("Reservoir area", area_options)

year_options = sorted(data["iso_aar"].unique(), reverse=True)
selected_year = st.selectbox("Year", year_options)

# Map readable measurement names to the corresponding dataframe columns.
measure_options = {
	"Filling level (%)": "fyllingsgrad_prosent",
	"Filled amount (TWh)": "fylling_TWh",
	"Change from previous week (%)": "endring_fyllingsgrad_prosent",
}

# Allow the user to select one measurement or view all measurements together.
selected_measure = st.selectbox(
	"Measure",
	["All measurements", *measure_options],
)

# Filter the data based on the selected area and year.
filtered_data = data[
	(data["omrnr"] == selected_area) & (data["iso_aar"] == selected_year)
].sort_values("dato_Id")

if filtered_data.empty:
	st.info("No data is available for the selected area and year.")
	st.stop()

# Create the month choices available for the selected area and year.
month_options = sorted(
	filtered_data["dato_Id"].dt.to_period("M").astype(str).unique()
)

# Select a month range, starting with the first available month by default.
selected_months = st.select_slider(
	"Month range",
	options=month_options,
	value=(month_options[0], month_options[0]),
)

# Keep observations inside the selected month range.
filtered_data = filtered_data[
	filtered_data["dato_Id"].dt.to_period("M").astype(str).between(
		selected_months[0], selected_months[1]
	)
]

# Create a plot containing all measurements if that option was selected.
if selected_measure == "All measurements":
	figure = px.line(
		filtered_data,
		x="dato_Id",
		y=list(measure_options.values()),
		markers=True,
		labels={"dato_Id": "Date", "value": "Measurement"},
		title=f"All measurements - Area {selected_area}, {selected_year}",
	)
else:
	# Otherwise, create a plot for the selected measurement.
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

# Apply consistent formatting to make the chart easier to read.
figure.update_layout(
	height=600,
	hovermode="x unified",
	plot_bgcolor="#F2FBFA",
	margin={"l": 30, "r": 30, "t": 70, "b": 30},
)

# Display the interactive Plotly chart directly in Streamlit.
st.plotly_chart(figure, width="stretch")
