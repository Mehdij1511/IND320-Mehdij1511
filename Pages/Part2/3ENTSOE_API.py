from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from entsoe_data import (
	PARTNER_DOMAINS,
	NORWEGIAN_DOMAINS,
	fetch_physical_flow,
)


st.title("Part 2 - ENTSO-E API")
st.write("Retrieve cross-border physical electricity flows involving Norway.")

partner = st.selectbox(
	"Partner connection",
	sorted(PARTNER_DOMAINS),
	index=sorted(PARTNER_DOMAINS).index("SE3"),
)
norwegian_zone = st.selectbox(
	"Norwegian bidding zone",
	sorted(NORWEGIAN_DOMAINS),
	index=sorted(NORWEGIAN_DOMAINS).index("NO4"),
)
start_date = st.date_input("Start date", value=date(2024, 1, 1))
end_date = st.date_input("End date", value=date(2024, 1, 7))

if st.button("Load ENTSO-E data", type="primary"):
	if end_date <= start_date:
		st.error("End date must be after start date.")
		st.stop()

	start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
	end = datetime.combine(end_date, time.min, tzinfo=timezone.utc)
	frames = []
	for in_domain, out_domain, direction in (
		(
			PARTNER_DOMAINS[partner],
			NORWEGIAN_DOMAINS[norwegian_zone],
			"Into Norway",
		),
		(
			NORWEGIAN_DOMAINS[norwegian_zone],
			PARTNER_DOMAINS[partner],
			"Out of Norway",
		),
	):
		try:
			frames.append(
				fetch_physical_flow(
					in_domain,
					out_domain,
					start,
					end,
					f"{partner}-{norwegian_zone}",
					direction,
				)
			)
		except (RuntimeError, ValueError, requests.RequestException) as error:
			st.error(f"Could not load {direction.lower()} data: {error}")
			st.stop()

	data = pd.concat(frames, ignore_index=True)
	if data.empty:
		st.warning("ENTSO-E returned no observations for this selection.")
	else:
		figure = px.line(
			data,
			x="timestamp",
			y="quantity_mw",
			color="direction",
			markers=True,
			labels={
				"timestamp": "Time (UTC)",
				"quantity_mw": "Physical flow (MW)",
				"direction": "Direction",
			},
			title=f"{partner} - {norwegian_zone} physical flow",
		)
		st.plotly_chart(figure, width="stretch")
		st.dataframe(data, hide_index=True, width="stretch")
