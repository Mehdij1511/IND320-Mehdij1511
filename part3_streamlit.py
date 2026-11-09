from datetime import date

import pandas as pd
import streamlit as st

from mongo_data import load_era5_weather_cache, save_era5_weather_cache
from nve_data import load_reservoir_data
from part3_data import download_era5_data


def select_electricity_area(key_prefix: str) -> tuple[pd.DataFrame, int]:
    data = load_reservoir_data()
    electricity_data = data.loc[data["omrType"] == "EL"]
    area_numbers = sorted(electricity_data["omrnr"].dropna().unique())
    if not area_numbers:
        raise ValueError("Magasinstatistikk contains no electricity areas.")

    area_number = st.selectbox(
        "Electricity area",
        options=area_numbers,
        format_func=lambda value: f"NO{int(value)}",
        key=f"{key_prefix}_area",
    )
    return electricity_data, int(area_number)


def reservoir_filling_series(
    electricity_data: pd.DataFrame,
    area_number: int,
) -> pd.Series:
    area_data = electricity_data.loc[
        electricity_data["omrnr"] == area_number
    ].sort_values("dato_Id")
    if area_data.empty:
        raise ValueError(f"Magasinstatistikk contains no data for NO{area_number}.")

    return area_data.set_index("dato_Id")["fyllingsgrad"]


@st.cache_data(
    ttl="1d",
    max_entries=5,
    show_spinner="Downloading ERA5 data from Open-Meteo...",
)
def load_weather_for_area(area_number: int, year: int) -> pd.DataFrame:
    samples_per_region = 1000
    random_seed = 42
    shared_cache = load_era5_weather_cache(
        area_number,
        year,
        samples_per_region,
        random_seed,
    )
    if shared_cache is not None:
        return shared_cache

    data = download_era5_data(
        region_identifier=f"NO{area_number}",
        start_date=date(year, 1, 1).isoformat(),
        end_date=date(year, 12, 31).isoformat(),
        samples_per_region=samples_per_region,
        random_seed=random_seed,
    )
    save_era5_weather_cache(
        area_number,
        year,
        samples_per_region,
        random_seed,
        data,
    )
    return data
