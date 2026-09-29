from pathlib import Path

import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	return data


st.title("Data table")
st.write("Explore the reservoir measurements using the filters below.")

data = load_data()

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

filtered_data = data[
	data["omrnr"].isin(selected_areas)
	& data["iso_aar"].between(*selected_year_range)
]

if filtered_data.empty:
	st.info("No data matches the selected filters.")
else:
	first_month = filtered_data["dato_Id"].min().to_period("M")
	first_month_data = filtered_data[
		filtered_data["dato_Id"].dt.to_period("M") == first_month
	].sort_values("dato_Id")

	series_columns = {
		"Filling level (%)": "fyllingsgrad_prosent",
		"Capacity (TWh)": "kapasitet_TWh",
		"Filled (TWh)": "fylling_TWh",
		"Change from previous week (%)": "endring_fyllingsgrad",
	}
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
				y_min=0,
			),
		},
		hide_index=True,
		use_container_width=True,
	)
