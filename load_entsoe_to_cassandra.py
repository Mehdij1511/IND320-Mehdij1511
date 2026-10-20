from datetime import datetime, timedelta, timezone

import requests

from cassandra_data import connect, initialize_schema, insert_electricity_flow
from entsoe_data import (
	NORWEGIAN_DOMAINS,
	PARTNER_DOMAINS,
	fetch_physical_flow,
)


START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2025, 2, 1, tzinfo=timezone.utc)
CHUNK_DAYS = 31
CONNECTIONS = {
	"SE3-NO4": (
		PARTNER_DOMAINS["SE3"],
		NORWEGIAN_DOMAINS["NO4"],
	),
	"SE2-NO3": (
		PARTNER_DOMAINS["SE2"],
		NORWEGIAN_DOMAINS["NO3"],
	),
	"DK1-NO2": (
		PARTNER_DOMAINS["DK1"],
		NORWEGIAN_DOMAINS["NO2"],
	),
}


def main() -> None:
	cluster, session = connect()
	try:
		initialize_schema(session)
		total_rows = 0
		for connection, (partner_domain, norway_domain) in CONNECTIONS.items():
			chunk_start = START
			while chunk_start < END:
				chunk_end = min(
					chunk_start + timedelta(days=CHUNK_DAYS),
					END,
				)
				directions = (
					(
						partner_domain,
						norway_domain,
						"Into Norway",
					),
					(
						norway_domain,
						partner_domain,
						"Out of Norway",
					),
				)

				for in_domain, out_domain, direction in directions:
					try:
						data = fetch_physical_flow(
							in_domain,
							out_domain,
							chunk_start,
							chunk_end,
							connection,
							direction,
						)
					except (RuntimeError, requests.RequestException) as error:
						print(
							f"{connection} {direction} failed for "
							f"{chunk_start.date()} to {chunk_end.date()}: {error}"
						)
						continue
					for _, row in data.iterrows():
						insert_electricity_flow(session, row.to_dict())
					total_rows += len(data)
					print(
						f"{connection} {chunk_start.date()} to {chunk_end.date()} "
						f"{direction}: {len(data)} rows"
					)
				chunk_start = chunk_end

		print(f"Finished inserting {total_rows} ENTSO-E rows")
	finally:
		cluster.shutdown()


if __name__ == "__main__":
	main()
