from cassandra.cluster import Cluster, Session


KEYSPACE = "ind320"


def connect(host: str = "127.0.0.1", port: int = 9042) -> tuple[Cluster, Session]:
	"""Connect to the local Cassandra container."""
	cluster = Cluster([host], port=port)
	return cluster, cluster.connect()


def initialize_schema(session: Session) -> None:
	"""Create the keyspace and tables used by the Part 2 pipeline."""
	session.execute(
		f"""
		CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
		WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
		"""
	)
	session.set_keyspace(KEYSPACE)
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS reservoir_observations (
			area_type text,
			area_number int,
			observation_date date,
			year int,
			week int,
			filling_level double,
			capacity_twh double,
			filled_twh double,
			previous_week_filling double,
			change_filling double,
			PRIMARY KEY ((area_type, area_number), observation_date)
		)
		"""
	)
	session.execute(
		"""
		CREATE TABLE IF NOT EXISTS electricity_flows (
			connection text,
			direction text,
			timestamp timestamp,
			quantity_mw double,
			resolution text,
			PRIMARY KEY ((connection, direction), timestamp)
		)
		"""
	)


def insert_reservoir_observation(session: Session, row: dict) -> None:
	"""Insert one normalized NVE observation."""
	session.execute(
		"""
		INSERT INTO reservoir_observations (
			area_type, area_number, observation_date, year, week,
			filling_level, capacity_twh, filled_twh,
			previous_week_filling, change_filling
		) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",
		(
			row["area_type"],
			int(row["area_number"]),
			row["observation_date"],
			int(row["year"]),
			int(row["week"]),
			float(row["filling_level"]),
			float(row["capacity_twh"]),
			float(row["filled_twh"]),
			float(row["previous_week_filling"]),
			float(row["change_filling"]),
		),
	)


def insert_electricity_flow(session: Session, row: dict) -> None:
	"""Insert one normalized ENTSO-E observation."""
	session.execute(
		"""
		INSERT INTO electricity_flows (
			connection, direction, timestamp, quantity_mw, resolution
		) VALUES (%s, %s, %s, %s, %s)
		""",
		(
			row["connection"],
			row["direction"],
			row["timestamp"].to_pydatetime()
			if hasattr(row["timestamp"], "to_pydatetime")
			else row["timestamp"],
			float(row["quantity_mw"]),
			row["resolution"],
		),
	)
