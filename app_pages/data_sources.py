import streamlit as st


st.title("Sources and data lineage")
st.write(
    "This page summarizes where the application's data comes from and how it "
    "moves through the analysis pipeline."
)

st.subheader("Reservoirs")
st.markdown(
    """
    **NVE Magasinstatistikk** provides public reservoir observations. The app uses
    this source for reservoir tables, plots, snapshots, and seasonality analysis.
    """
)

st.subheader("Weather")
st.markdown(
    """
    **Open-Meteo ERA5 Archive** provides hourly precipitation and temperature.
    Completed requests are cached locally and, when configured, shared through
    MongoDB so later app instances can reuse downloaded results.
    """
)

st.subheader("Electricity flows")
st.markdown(
    """
    **ENTSO-E Transparency Platform** provides live cross-border physical flows.
    Raw observations can be stored in Cassandra, aggregated with Spark into monthly
    totals, and stored in MongoDB for the monthly flow analysis.
    """
)

st.subheader("Storage and processing")
st.markdown(
    """
    - **Cassandra:** Raw electricity-flow observations
    - **Spark:** Monthly aggregation and energy conversion
    - **MongoDB:** Processed flows and shared ERA5 cache
    - **Streamlit:** Integrated user interface and interactive controls
    """
)
