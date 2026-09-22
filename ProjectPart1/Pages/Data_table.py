from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


DATA_FILE = Path(__file__).parents[1] / "Data" / "reservoirs.csv"


@st.cache_data
def load_data():
	data = pd.read_csv(DATA_FILE, parse_dates=["dato_Id"])
	data["fyllingsgrad_prosent"] = data["fyllingsgrad"] * 100
	return data


st.title("Data table")
st.write("Explore the reservoir data using the filters below.")

data = load_data()

area_options = sorted(data["omrnr"].unique())
selected_areas = st.multiselect(
	"Reservoir area",
	options=area_options,
	default=area_options,
)

year_options = sorted(data["iso_aar"].unique())
selected_years = st.multiselect(
	"Year",
	options=year_options,
	default=year_options,
)

filtered_data = data[
	data["omrnr"].isin(selected_areas) & data["iso_aar"].isin(selected_years)
]

display_data = filtered_data[
	[
		"dato_Id",
		"omrnr",
		"iso_aar",
		"iso_uke",
		"fyllingsgrad_prosent",
		"kapasitet_TWh",
		"fylling_TWh",
		"endring_fyllingsgrad",
	]
].rename(
	columns={
		"dato_Id": "Date",
		"omrnr": "Area",
		"iso_aar": "Year",
		"iso_uke": "Week",
		"fyllingsgrad_prosent": "Filling level (%)",
		"kapasitet_TWh": "Capacity (TWh)",
		"fylling_TWh": "Filled (TWh)",
		"endring_fyllingsgrad": "Change from previous week",
	}
)

rows_per_page = 200
page_count = max(1, (len(display_data) + rows_per_page - 1) // rows_per_page)
current_page = min(st.session_state.get("data_table_page", 0), page_count - 1)
st.session_state.data_table_page = current_page

previous_button, status, next_button = st.columns([1, 2, 1])
with previous_button:
	if st.button("Previous", disabled=current_page == 0, use_container_width=True):
		st.session_state.data_table_page -= 1
		st.rerun()
with status:
	start_index = current_page * rows_per_page
	end_index = min(start_index + rows_per_page, len(display_data))
	st.write(f"Showing rows {start_index + 1}-{end_index} of {len(display_data):,}")
with next_button:
	if st.button("Next", disabled=current_page >= page_count - 1, use_container_width=True):
		st.session_state.data_table_page += 1
		st.rerun()

page_data = display_data.iloc[start_index:end_index]

table_html = page_data.to_html(index=False, classes="data-table", border=0)
table_html = f"""
<style>
body {{ margin: 0; font-family: sans-serif; }}
.data-table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
.data-table th {{ background: #008571; color: white; cursor: pointer; padding: 8px; text-align: left; position: sticky; top: 0; }}
.data-table td {{ border-bottom: 1px solid #d5e5e2; padding: 7px 8px; white-space: nowrap; }}
.data-table tr:nth-child(even) {{ background: #f2fbfa; }}
.data-table th.sort-ascending::after {{ content: "  ▲"; }}
.data-table th.sort-descending::after {{ content: "  ▼"; }}
</style>
{table_html}
<script>
const table = document.querySelector(".data-table");
const headers = table.querySelectorAll("thead th");
const body = table.querySelector("tbody");

headers.forEach((header, columnIndex) => {{
	header.addEventListener("click", () => {{
		const descending = header.classList.contains("sort-ascending");
		headers.forEach((item) => item.classList.remove("sort-ascending", "sort-descending"));
		header.classList.add(descending ? "sort-descending" : "sort-ascending");

		const rows = Array.from(body.querySelectorAll("tr"));
		rows.sort((rowA, rowB) => {{
			const valueA = rowA.cells[columnIndex].textContent.trim();
			const valueB = rowB.cells[columnIndex].textContent.trim();
			const numberA = Number(valueA);
			const numberB = Number(valueB);
			const bothNumbers = valueA !== "" && valueB !== "" && !Number.isNaN(numberA) && !Number.isNaN(numberB);
			const comparison = bothNumbers
				? numberA - numberB
				: valueA.localeCompare(valueB, undefined, {{ numeric: true, sensitivity: "base" }});
			return descending ? -comparison : comparison;
		}});
		rows.forEach((row) => body.appendChild(row));
	}});
}});
</script>
"""

components.html(table_html, height=700, scrolling=True)
