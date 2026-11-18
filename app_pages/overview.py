import streamlit as st


st.title("Portfolio overview")
st.write(
    "Explore Norwegian reservoir data, weather observations, and electricity flows "
    "through the analysis-based navigation in the sidebar."
)

nve, weather, entsoe, mongo = st.columns(4)
nve.metric("NVE", "Reservoir data")
weather.metric("Open-Meteo", "ERA5 weather")
entsoe.metric("ENTSO-E", "Physical flows")
mongo.metric("MongoDB", "Processed flows")

st.subheader("Application structure")
st.markdown(
    """
    - **Reservoirs:** NVE table, interactive plot, snapshot, and seasonality.
    - **Weather:** Open-Meteo/ERA5 precipitation outliers and temperature anomalies.
    - **Electricity flows:** Live ENTSO-E physical flows and Spark/MongoDB monthly summaries.
    - **Data sources:** APIs, databases, caching, and processing lineage.
    """
)