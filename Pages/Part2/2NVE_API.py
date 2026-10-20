import streamlit as st
from nve_data import AREA_TYPE_LABELS, load_reservoir_data


st.title("Part 2 - NVE API")
st.write("Select an NVE area type, area number, and date range.")

data = load_reservoir_data()
area_type = st.selectbox(
	"Area type",
	sorted(data["omrType"].unique()),
	format_func=lambda value: AREA_TYPE_LABELS.get(value, value),
)
area_numbers = sorted(data.loc[data["omrType"] == area_type, "omrnr"].unique())
area_number = st.selectbox("Area number", area_numbers)

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
	width="stretch",
)
st.dataframe(filtered, hide_index=True, width="stretch")
