from datetime import datetime, timedelta, timezone
import re
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st


ENTSOE_URL = "https://web-api.tp.entsoe.eu/api"

NORWEGIAN_DOMAINS = {
	"NO1": "10YNO-1--------2",
	"NO2": "10YNO-2--------T",
	"NO3": "10YNO-3--------J",
	"NO4": "10YNO-4--------9",
	"NO5": "10Y1001A1001A48H",
}

PARTNER_DOMAINS = {
	"SE3": "10Y1001A1001A44P",
	"SE2": "10Y1001A1001A45N",
	"DK1": "10YDK-1--------W",
	"DK2": "10YDK-2--------M",
	"FI": "10YFI-1--------U",
	"NL": "10YNL----------L",
}


def _resolution_delta(resolution: str) -> pd.Timedelta:
	match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", resolution)
	if not match:
		raise ValueError(f"Unsupported ENTSO-E resolution: {resolution}")
	hours = int(match.group(1) or 0)
	minutes = int(match.group(2) or 0)
	return pd.Timedelta(hours=hours, minutes=minutes)


def _secret_token() -> str:
	try:
		token = st.secrets["ENTSOE_SECURITY_TOKEN"]
	except KeyError as error:
		raise RuntimeError(
			"ENTSOE_SECURITY_TOKEN is missing from Streamlit secrets."
	) from error

	if not token or token.startswith("paste-") or token.startswith("your-"):
		raise RuntimeError(
			"ENTSOE_SECURITY_TOKEN must contain a valid ENTSO-E token."
		)
	return token


def _parse_xml(xml_text: str, connection: str, direction: str) -> pd.DataFrame:
	root = ET.fromstring(xml_text)
	rows = []

	for time_series in root.iter():
		if time_series.tag.rsplit("}", 1)[-1] != "TimeSeries":
			continue

		for period in time_series.iter():
			if period.tag.rsplit("}", 1)[-1] != "Period":
				continue

			start = None
			resolution = "PT60M"
			for child in period.iter():
				name = child.tag.rsplit("}", 1)[-1]
				if name == "start":
					start = child.text
				elif name == "resolution":
					resolution = child.text or resolution

			if not start:
				continue

			start_time = pd.Timestamp(start)
			if start_time.tzinfo is None:
				start_time = start_time.tz_localize("UTC")
			else:
				start_time = start_time.tz_convert("UTC")

			for point in period.iter():
				if point.tag.rsplit("}", 1)[-1] != "Point":
					continue
				position = quantity = None
				for child in point:
					name = child.tag.rsplit("}", 1)[-1]
					if name == "position":
						position = child.text
					elif name in {"quantity", "outBiddingZone_Domain.mRID"}:
						quantity = child.text

				if position and quantity:
					rows.append(
						{
							"timestamp": start_time,
							"position": int(position),
							"quantity_mw": float(quantity),
							"resolution": resolution,
							"connection": connection,
							"direction": direction,
						}
					)

	if not rows:
		return pd.DataFrame(
			columns=[
				"timestamp",
				"position",
				"quantity_mw",
				"resolution",
				"connection",
				"direction",
			]
		)

	data = pd.DataFrame(rows)
	data["timestamp"] = data["timestamp"] + (
		(data["position"] - 1)
		* data["resolution"].map(_resolution_delta)
	)
	return data.sort_values("timestamp").reset_index(drop=True)


@st.cache_data(ttl=3600)
def fetch_physical_flow(
	in_domain: str,
	out_domain: str,
	start: datetime,
	end: datetime,
	connection: str,
	direction: str,
) -> pd.DataFrame:
	"""Fetch ENTSO-E physical flows for one direction and date range."""
	params = {
		"securityToken": _secret_token(),
		"documentType": "A11",
		"in_Domain": in_domain,
		"out_Domain": out_domain,
		"periodStart": start.strftime("%Y%m%d%H%M"),
		"periodEnd": end.strftime("%Y%m%d%H%M"),
	}
	response = requests.get(ENTSOE_URL, params=params, timeout=20)
	if response.status_code == 401:
		raise RuntimeError(
			"ENTSO-E rejected the security token (HTTP 401). "
			"Generate a valid token in the ENTSO-E Transparency Platform "
			"and update .streamlit/secrets.toml."
		)
	response.raise_for_status()

	if "Acknowledgement_MarketDocument" in response.text:
		root = ET.fromstring(response.text)
		reason = next(
			(
				element.text
				for element in root.iter()
				if element.tag.rsplit("}", 1)[-1] == "text" and element.text
			),
			"ENTSO-E returned an acknowledgement without a reason.",
		)
		if "No matching data found" in reason:
			return pd.DataFrame(
				columns=[
					"timestamp",
					"position",
					"quantity_mw",
					"resolution",
					"connection",
					"direction",
				]
			)
		raise RuntimeError(f"ENTSO-E rejected the request: {reason}")

	return _parse_xml(response.text, connection, direction)


@st.cache_data(ttl=3600)
def load_entsoe_flows(days: int = 7) -> pd.DataFrame:
	"""Load recent flows in both directions for configured Norway connections."""
	end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
	start = end - timedelta(days=days)
	frames = []

	for norway_name, norway_domain in NORWEGIAN_DOMAINS.items():
		for partner_name, partner_domain in PARTNER_DOMAINS.items():
			connection = f"{partner_name}-{norway_name}"
			for in_domain, out_domain, direction in (
				(partner_domain, norway_domain, "Into Norway"),
				(norway_domain, partner_domain, "Out of Norway"),
			):
				frames.append(
					fetch_physical_flow(
						in_domain,
						out_domain,
						start,
						end,
						connection,
						direction,
					)
				)

	data = pd.concat(frames, ignore_index=True)
	if data.empty:
		raise RuntimeError("ENTSO-E returned no physical-flow observations.")
	return data
