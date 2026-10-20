import requests
import pandas as pd
import streamlit as st


NVE_DATA_URL = (
    "https://biapi.nve.no/magasinstatistikk/api/"
    "Magasinstatistikk/HentOffentligData"
)

AREA_TYPE_LABELS = {
	"EL": "Electricity region",
	"NO": "Norway",
	"VASS": "Watercourse",
}


@st.cache_data(ttl=3600)
def load_reservoir_data() -> pd.DataFrame:
	"""Fetch public reservoir observations from NVE."""
	response = requests.get(NVE_DATA_URL, timeout=30)
	response.raise_for_status()
	data = pd.DataFrame(response.json())

	if data.empty:
		raise ValueError("NVE API returned no reservoir observations.")

	data["dato_Id"] = pd.to_datetime(data["dato_Id"], errors="raise")
	return data
