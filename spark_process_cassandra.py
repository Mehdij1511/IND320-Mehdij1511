import json
from pathlib import Path

from cassandra_data import connect
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
	col,
	month,
	regexp_extract,
	sum as spark_sum,
	to_timestamp,
	when,
	year,
)


def main() -> None:
	cluster, session = connect()
	try:
		rows = session.execute(
			"""
			SELECT connection, direction, timestamp, quantity_mw, resolution
			FROM ind320.electricity_flows
			"""
		)
		records = [row._asdict() for row in rows]
	finally:
		cluster.shutdown()

	if not records:
		raise RuntimeError("Cassandra contains no ENTSO-E electricity-flow rows.")

	spark = (
		SparkSession.builder
		.appName("IND320-Cassandra-Processing")
		.master("local[*]")
		.getOrCreate()
	)

	try:
		flows = spark.createDataFrame(records)
		flows = flows.withColumn("timestamp", to_timestamp(col("timestamp")))
		processed = (
			flows.withColumn("year", year("timestamp"))
			.withColumn("month", month("timestamp"))
			.withColumn(
				"interval_hours",
				when(col("resolution") == "PT15M", 0.25)
				.when(col("resolution") == "PT30M", 0.5)
				.when(
					col("resolution").rlike(r"^PT\d+H$")
					& (regexp_extract(col("resolution"), r"PT(\d+)H", 1) != ""),
					regexp_extract(col("resolution"), r"PT(\d+)H", 1)
					.cast("double"),
				)
				.otherwise(1.0),
			)
			.withColumn("energy_mwh", col("quantity_mw") * col("interval_hours"))
		)

		monthly = (
			processed.groupBy("connection", "year", "month", "direction")
			.agg(spark_sum("energy_mwh").alias("total_energy_mwh"))
			.orderBy("connection", "year", "month", "direction")
		)

		print("Spark input rows:", flows.count())
		print("Spark output rows:", monthly.count())
		monthly.show(truncate=False)

		output_directory = Path("data/processed/electricity_flows")
		output_directory.mkdir(parents=True, exist_ok=True)
		output_file = output_directory / "monthly_flows.json"
		records = [
			{
				"connection": row["connection"],
				"year": int(row["year"]),
				"month": int(row["month"]),
				"direction": row["direction"],
				"total_energy_mwh": float(row["total_energy_mwh"]),
			}
			for row in monthly.collect()
		]
		output_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
		print(f"Processed data written to {output_file}")
	finally:
		spark.stop()


if __name__ == "__main__":
	main()
