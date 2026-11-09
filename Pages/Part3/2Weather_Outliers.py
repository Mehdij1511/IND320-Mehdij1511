import streamlit as st

from mongo_data import era5_mongodb_cache_configured
from part3_analysis import plot_precipitation_outliers, plot_temperature_anomalies
from part3_streamlit import load_weather_for_area, select_electricity_area
from part3_data import Era5ApiBudgetExceeded


st.title("Part 3 - Weather outliers")
st.write(
    "Download hourly ERA5 precipitation and temperature for the selected "
    "Magasinstatistikk electricity area."
)

_, area_number = select_electricity_area("part3_weather")
year = st.selectbox("Weather data year", options=[2024], key="part3_weather_year")
st.caption(
    "New requests use conservative rolling budgets of 4,500 calls per hour and "
    "9,500 calls per 24 hours, below Open-Meteo's published limits. "
    "Completed batches and full area/year results are cached locally and shared "
    "across app instances through MongoDB when configured. "
    "Rate-limited requests are not retried automatically."
)
if not era5_mongodb_cache_configured():
    st.info(
        "MONGODB_URI is not configured, so the shared cache and request budget "
        "are local to this app instance."
    )

# Keep the historical API request behind explicit user confirmation.
if st.button(
    f"Download or load NO{area_number} weather data",
    type="primary",
    key="part3_weather_download",
):
    try:
        with st.spinner(
            "Checking cached ERA5 batches and downloading any missing data. "
            "This can take several minutes; completed batches are reused.",
            show_time=True,
        ):
            weather_data = load_weather_for_area(area_number, year)
    except Era5ApiBudgetExceeded as error:
        st.warning(str(error))
    else:
        st.session_state["part3_weather_data"] = weather_data
        st.session_state["part3_weather_selection"] = (area_number, year)

weather_selection = st.session_state.get("part3_weather_selection")
weather_data = st.session_state.get("part3_weather_data")
if weather_selection != (area_number, year):
    weather_data = None

precipitation_tab, temperature_tab = st.tabs(
    ["Precipitation SPC", "Temperature LOF"],
    on_change="rerun",
)

if precipitation_tab.open:
    st.subheader("Precipitation outliers and SPC limits")
    frequency_cutoff = st.slider(
        "DCT frequency cut-off",
        min_value=1,
        max_value=1000,
        value=52,
        key="part3_spc_cutoff",
    )
    standard_deviations = st.slider(
        "Number of robust standard deviations",
        min_value=1.0,
        max_value=6.0,
        value=3.0,
        step=0.25,
        key="part3_spc_std",
    )
    if weather_data is None:
        st.info("Download the selected area's weather data to view this analysis.")
    else:
        figure, summary, outliers = plot_precipitation_outliers(
            weather_data,
            frequency_cutoff=frequency_cutoff,
            n_standard_deviations=standard_deviations,
        )
        st.pyplot(figure, clear_figure=True)
        st.metric(
            "Precipitation outliers",
            summary["outliers"],
            f"{summary['outlier_percentage']:.2f}% of observations",
        )
        st.dataframe(outliers, hide_index=True, width="stretch")

if temperature_tab.open:
    st.subheader("Temperature anomalies using Local Outlier Factor")
    contamination = st.slider(
        "Expected anomaly proportion",
        min_value=0.001,
        max_value=0.10,
        value=0.01,
        step=0.001,
        format="%.3f",
        key="part3_lof_contamination",
    )
    if weather_data is None:
        st.info("Download the selected area's weather data to view this analysis.")
    else:
        figure, summary, anomalies = plot_temperature_anomalies(
            weather_data,
            contamination=contamination,
        )
        st.pyplot(figure, clear_figure=True)
        st.metric(
            "Temperature anomalies",
            summary["anomalies"],
            f"{summary['anomaly_percentage']:.2f}% of observations",
        )
        st.dataframe(anomalies, hide_index=True, width="stretch")
