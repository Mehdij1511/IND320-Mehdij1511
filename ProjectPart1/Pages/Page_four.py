from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Locate the CSV file relative to this page so the app works from the project root.
DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	"""Load the reservoir data and prepare the percentage values."""
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])

	# Convert the filling level from a decimal value to a percentage.
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	return data

# Introduce the purpose of this additional analysis page.
st.title("Reservoir snapshot")
st.write("A quick view of reservoir conditions across Norway.")

# Load the data using Streamlit caching to avoid reading the file repeatedly.
data = load_data()

# Let the user select which year should be shown in the summary.
year_options = sorted(data["iso_aar"].unique(), reverse=True)
selected_year = st.selectbox("Year", year_options)

# Keep only observations from the selected year.
year_data = data[data["iso_aar"] == selected_year]

# Use the most recent observation available for the selected year.
latest_date = year_data["dato_Id"].max()
latest_data = year_data[year_data["dato_Id"] == latest_date]

# Calculate the main summary values shown at the top of the page.
average_filling = latest_data["fyllingsgrad_prosent"].mean()
total_capacity = latest_data["kapasitet_TWh"].sum()
total_filled = latest_data["fylling_TWh"].sum()

# Display the summary values as three separate metrics.
metric_one, metric_two, metric_three = st.columns(3)
metric_one.metric("Average filling", f"{average_filling:.1f}%")
metric_two.metric("Total capacity", f"{total_capacity:.1f} TWh")
metric_three.metric("Filled volume", f"{total_filled:.1f} TWh")

# Show the date used for the summary values.
st.caption(f"Latest observation in {selected_year}: {latest_date:%d %B %Y}")

# Calculate the average filling level for each reservoir area.
area_summary = (
	latest_data.groupby("omrnr", as_index=False)["fyllingsgrad_prosent"]
	.mean()
	.sort_values("fyllingsgrad_prosent", ascending=False)
)

# Create a bar chart to compare filling levels between reservoir areas.
figure = px.bar(
    area_summary,
    x="omrnr",
    y="fyllingsgrad_prosent",
    text_auto=".1f",
    labels={"omrnr": "Reservoir area", "fyllingsgrad_prosent": "Filling level (%)"},
    title="Filling level by reservoir area",
)

# Apply consistent formatting to make the chart easier to read.
figure.update_layout(
    height=500,
    plot_bgcolor="#F2FBFA",
    margin={"l": 30, "r": 30, "t": 70, "b": 30},
)

# Display the interactive chart in the Streamlit app.
st.plotly_chart(figure, width="stretch")