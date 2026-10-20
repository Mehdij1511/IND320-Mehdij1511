import pandas as pd
import streamlit as st
from nve_data import AREA_TYPE_LABELS, load_reservoir_data


def load_data():
	"""Load reservoir observations and prepare percentage values."""
	data = load_reservoir_data().copy()
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

# Let the user filter the table by area type, area number, and year.
area_type_options = sorted(data["omrType"].unique())
selected_area_type = st.selectbox(
	"Area type",
	area_type_options,
	format_func=lambda value: AREA_TYPE_LABELS.get(value, value),
)

area_options = sorted(
	data.loc[data["omrType"] == selected_area_type, "omrnr"].unique()
)
selected_areas = st.multiselect(
    "Area number",
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
	(data["omrType"] == selected_area_type)
	& data["omrnr"].isin(selected_areas)
	& data["iso_aar"].between(*selected_year_range)
]

# Show a helpful message instead of an empty table when no data is found.
if filtered_data.empty:
	st.info("No data matches the selected filters.")
else:
	# Provide one overview row for every column imported from the NVE API.
	imported_columns = load_reservoir_data().columns
	column_summary = pd.DataFrame(
		{
			"Imported column": imported_columns,
			"Data type": [str(data[column].dtype) for column in imported_columns],
			"Non-null values": [
				int(filtered_data[column].notna().sum())
				for column in imported_columns
			],
			"Example value": [
				filtered_data[column].dropna().iloc[0]
				if not filtered_data[column].dropna().empty
				else None
				for column in imported_columns
			],
		}
	)

	st.caption("Each row below represents one column imported from the NVE API.")
	st.dataframe(
		column_summary,
		hide_index=True,
		width="stretch",
	)

	# Keep the filtered source rows available for users who want the imported values.
	st.subheader("Filtered imported data")
	st.dataframe(filtered_data, hide_index=True, width="stretch")
