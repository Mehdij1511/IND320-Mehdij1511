import plotly.express as px
import streamlit as st

from mongo_data import load_monthly_flows


st.title("Part 2 - MongoDB")
st.write(
	"Explore the monthly electricity-flow summaries prepared with Spark and "
	"stored in MongoDB Atlas."
)

try:
	data = load_monthly_flows()
except RuntimeError as error:
	st.error(str(error))
	st.stop()

required_columns = {
	"connection",
	"year",
	"month",
	"direction",
	"total_energy_mwh",
}
missing_columns = required_columns.difference(data.columns)
if missing_columns:
	st.error(f"MongoDB data is missing columns: {sorted(missing_columns)}")
	st.stop()

connections = sorted(data["connection"].unique())
years = sorted(data["year"].unique())

left, right = st.columns(2)

with left:
	st.subheader("Annual electricity transfer")
	selected_connection = st.radio(
		"Connection",
		connections,
		horizontal=True,
	)
	selected_year = st.selectbox("Year", years)

	annual_data = data[
		(data["connection"] == selected_connection)
		& (data["year"] == selected_year)
	]
	annual_figure = px.pie(
		annual_data,
		names="direction",
		values="total_energy_mwh",
		title=f"{selected_connection} - {selected_year}",
		hole=0.35,
	)
	st.plotly_chart(annual_figure, width="stretch")

with right:
	st.subheader("Monthly electricity transfer")
	available_months = sorted(
		data.loc[
			(data["connection"] == selected_connection)
			& (data["year"] == selected_year),
			"month",
		].unique()
	)
	selected_months = st.pills(
		"Months",
		available_months,
		default=available_months,
		selection_mode="multi",
		format_func=lambda month_number: f"Month {month_number}",
	)

	if not selected_months:
		st.info("Select at least one month.")
	else:
		monthly_data = data[
			(data["connection"] == selected_connection)
			& (data["year"] == selected_year)
			& data["month"].isin(selected_months)
		].sort_values("month")
		monthly_figure = px.line(
			monthly_data,
			x="month",
			y="total_energy_mwh",
			color="direction",
			markers=True,
			labels={
				"month": "Month",
				"total_energy_mwh": "Total energy (MWh)",
				"direction": "Direction",
			},
			title=f"{selected_connection} - monthly transfer",
		)
		st.plotly_chart(monthly_figure, width="stretch")

with st.expander("About the data"):
	st.write(
		"The source data was retrieved from the ENTSO-E Transparency Platform API. "
		"Raw electricity-flow observations were stored in Cassandra. Spark converted "
		"the observations to MWh, added year and month fields, and aggregated the "
		"quantities by connection, period, and direction. The processed records were "
		"then stored in MongoDB Atlas for this Streamlit page. "
		"SE3-NO4 contains the complete two-year dataset required for the project. "
		"The other selected connections are included as verified comparison "
		"connections, but could not be loaded completely for the full two-year "
		"period because retrieving all of their API data took too long."
	)
