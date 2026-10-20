import json
from pathlib import Path

from mongo_data import connect_mongodb


INPUT_FILE = Path("data/processed/electricity_flows/monthly_flows.json")


def main() -> None:
	if not INPUT_FILE.exists():
		raise FileNotFoundError(
			f"Processed Spark output was not found: {INPUT_FILE}. "
			"Run spark_process_cassandra.py first."
		)

	documents = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
	client = connect_mongodb()
	try:
		collection = client["ind320"]["monthly_electricity_flows"]
		collection.delete_many({})
		if documents:
			collection.insert_many(documents)
		print(f"Inserted {len(documents)} documents into MongoDB.")
	finally:
		client.close()


if __name__ == "__main__":
	main()
