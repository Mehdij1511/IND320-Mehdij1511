import streamlit as st

from part3_analysis import plot_spectrogram, plot_stl_decomposition
from part3_streamlit import reservoir_filling_series, select_electricity_area


st.title("Part 3 - Reservoir seasonality")
st.write(
    "Explore the seasonal pattern in Magasinstatistikk filling levels using "
    "STL decomposition and a spectrogram."
)

electricity_data, area_number = select_electricity_area("part3_seasonality")
filling = reservoir_filling_series(electricity_data, area_number)

stl_tab, spectrogram_tab = st.tabs(
    ["STL decomposition", "Spectrogram"],
    on_change="rerun",
)

if stl_tab.open:
    st.subheader("Seasonal-trend decomposition using LOESS")
    st.caption("The series is weekly; a period of 52 represents one year.")
    seasonal = st.select_slider(
        "Seasonal smoother",
        options=list(range(7, 102, 2)),
        value=13,
        key="part3_stl_seasonal",
    )
    max_trend = min(501, (len(filling) - 1) // 2 * 2 + 1)
    if max_trend <= 52:
        raise ValueError("The selected area has too few observations for STL.")
    trend = st.select_slider(
        "Trend smoother",
        options=list(range(53, max_trend + 1, 2)),
        value=53,
        key="part3_stl_trend",
    )
    robust = st.toggle("Robust fitting", value=True, key="part3_stl_robust")
    figure, _ = plot_stl_decomposition(
        filling,
        seasonal=seasonal,
        trend=trend,
        robust=robust,
    )
    st.pyplot(figure, clear_figure=True)

if spectrogram_tab.open:
    st.subheader("Spectrogram")
    window_length = st.select_slider(
        "Window length (weeks)",
        options=[32, 64, 128, 256],
        value=64,
        key="part3_spectrogram_window",
    )
    window_length = min(window_length, len(filling))
    window_overlap = st.slider(
        "Window overlap (weeks)",
        min_value=0,
        max_value=window_length - 1,
        value=min(32, window_length - 1),
        key="part3_spectrogram_overlap",
    )
    figure = plot_spectrogram(
        filling,
        window_length=window_length,
        window_overlap=window_overlap,
    )
    st.pyplot(figure, clear_figure=True)
