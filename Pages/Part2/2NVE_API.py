import streamlit as st
from nve_data import AREA_TYPE_LABELS, load_reservoir_data


st.title("Part 2 - NVE API")
st.write(
	"Select an NVE area type, area number, and date range to retrieve and "
	"visualise reservoir observations."
)

# The API data is cached, while the selected date interval controls the
# observations used in the page and the amount of data displayed.
data = load_reservoir_data()
area_types = sorted(data["omrType"].dropna().unique())
area_type = st.radio(
	"Area type",
	area_types,
	format_func=lambda value: AREA_TYPE_LABELS.get(value, value),
	horizontal=True,
)

area_numbers = sorted(data.loc[data["omrType"] == area_type, "omrnr"].unique())
area_number = st.selectbox("Area number", area_numbers)

# Use the selected interval after the API response has been downloaded.
# The NVE endpoint returns the public dataset without date query parameters.
area_data = data[
	(data["omrType"] == area_type) & (data["omrnr"] == area_number)
].sort_values("dato_Id")
date_range = st.slider(
	"Date range",
	min_value=area_data["dato_Id"].min().date(),
	max_value=area_data["dato_Id"].max().date(),
	value=(area_data["dato_Id"].min().date(), area_data["dato_Id"].max().date()),
)

filtered = area_data[
	area_data["dato_Id"].dt.date.between(date_range[0], date_range[1])
]

st.line_chart(
	filtered.set_index("dato_Id")[["fyllingsgrad"]].rename(
		columns={"fyllingsgrad": "Filling level"}
	),
	x_label="Date",
	y_label="Filling level",
	width="stretch",
)

# Prepare one sparkline for every area number in the selected area type.
area_type_data = data[data["omrType"] == area_type].copy()
area_type_data = area_type_data[
	area_type_data["dato_Id"].dt.date.between(date_range[0], date_range[1])
]
line_chart_data = (
	area_type_data.sort_values("dato_Id")
	.groupby("omrnr")["fyllingsgrad"]
	.apply(list)
	.rename("Filling level")
	.reset_index()
)
st.subheader("Filling level by area number")
st.dataframe(
	line_chart_data,
	column_config={
		"Filling level": st.column_config.LineChartColumn(
			"Filling level",
			y_min=0,
			y_max=1,
			width="large",
		)
	},
	hide_index=True,
	width="stretch",
)

st.dataframe(filtered, hide_index=True, width="stretch")
