from pathlib import Path

import pandas as pd
import streamlit as st

# Locate the CSV file relative to this page so the app works from the project root.
DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	"""Load the reservoir observations and prepare percentage values."""
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	data["fyllingsgrad_forrige_uke_prosent"] = (
		data["fyllingsgrad_forrige_uke"] * 100
	)
	data["endring_fyllingsgrad_prosent"] = data["endring_fyllingsgrad"] * 100
	return data


st.title("Data table")
st.write("Explore the reservoir measurements using the filters below.")

# Load the data using Streamlit caching to avoid reading the file repeatedly.
data = load_data()

# Let the user filter the table by reservoir area and year.
area_options = sorted(data["omrnr"].unique())
selected_areas = st.multiselect(
    "Reservoir area",
    options=area_options,
    default=area_options,
)

year_options = sorted(data["iso_aar"].unique())
selected_year_range = st.slider(
    "Year range (from - to)",
    min_value=int(year_options[0]),
    max_value=int(year_options[-1]),
    value=(int(year_options[0]), int(year_options[-1])),
)

# Keep only the rows matching both selected filters.
filtered_data = data[
	data["omrnr"].isin(selected_areas)
	& data["iso_aar"].between(*selected_year_range)
]

# Show a helpful message instead of an empty table when no data is found.
if filtered_data.empty:
	st.info("No data matches the selected filters.")
else:
	# Select and sort all observations belonging to the first available month.
	first_month = filtered_data["dato_Id"].min().to_period("M")
	first_month_data = filtered_data[
		filtered_data["dato_Id"].dt.to_period("M") == first_month
	].sort_values("dato_Id")

    # Use readable labels in the table while keeping the original column names internally.
	series_columns = {
		"Filling level (%)": "fyllingsgrad_prosent",
		"Previous week filling (%)": "fyllingsgrad_forrige_uke_prosent",
		"Capacity (TWh)": "kapasitet_TWh",
		"Filled (TWh)": "fylling_TWh",
		"Change from previous week (%)": "endring_fyllingsgrad_prosent",
	}

	# Format one table row per measurement and one chart series per row.
	summary_data = pd.DataFrame(
		{
			"Measurement": list(series_columns),
			"First month": [
				first_month_data[column].round(3).tolist()
				for column in series_columns.values()
			],
		}
	)

	st.caption(f"Each row shows one measurement and its observations from {first_month}.")
	st.dataframe(
		summary_data,
		column_config={
			"First month": st.column_config.LineChartColumn(
				"First month data",
				width="large",
			),
		},
		hide_index=True,
		width="stretch",
	)

	# Keep the filtered source rows available for users who want the imported values.
	st.subheader("Filtered imported data")
	st.dataframe(filtered_data, hide_index=True, width="stretch")
