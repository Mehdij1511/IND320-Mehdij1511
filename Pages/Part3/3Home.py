import streamlit as st


st.title("Part 3 - Data quality")
st.write(
    "Part 3 combines historical ERA5 weather data with reservoir-filling "
    "observations from Magasinstatistikk."
)

st.subheader("Analyses")
st.markdown(
    """
    - **Reservoir seasonality:** Explore STL decomposition and a spectrogram of weekly filling levels.
    - **Weather outliers:** Download hourly ERA5 precipitation and temperature for an electricity area, then inspect SPC outliers and LOF anomalies.
    """
)

st.info(
    "Choose the electricity area from Magasinstatistikk on each analysis page. "
    "ERA5 weather data is downloaded only after confirmation and cached for one day."
)
