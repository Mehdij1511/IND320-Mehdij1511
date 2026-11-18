import gzip
import json
from datetime import datetime, timedelta, timezone
from time import monotonic, sleep
from uuid import uuid4

import streamlit as st
import pandas as pd
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError
from streamlit.errors import StreamlitSecretNotFoundError


def _mongodb_uri() -> str | None:
	try:
		uri = st.secrets["MONGODB_URI"]
	except (KeyError, StreamlitSecretNotFoundError):
		return None

	if not uri or uri.startswith("mongodb+srv://..."):
		raise RuntimeError("MONGODB_URI must contain a valid MongoDB URI.")
	return uri


@st.cache_resource(show_spinner=False)
def _shared_mongodb_client(uri: str) -> MongoClient:
	client = MongoClient(uri, serverSelectionTimeoutMS=10000)
	client.admin.command("ping")
	return client


def connect_era5_mongodb() -> MongoClient | None:
	"""Connect to the shared ERA5 cache when MongoDB secrets are configured."""
	uri = _mongodb_uri()
	if uri is None:
		return None
	return _shared_mongodb_client(uri)


def era5_mongodb_cache_configured() -> bool:
	"""Report whether this app can use shared MongoDB-backed ERA5 caching."""
	return _mongodb_uri() is not None


def connect_mongodb() -> MongoClient:
	"""Connect to MongoDB Atlas using the local or deployed secret."""
	uri = _mongodb_uri()
	if uri is None:
		raise RuntimeError(
			"MONGODB_URI is missing from Streamlit secrets."
		)

	client = MongoClient(uri, serverSelectionTimeoutMS=10000)
	client.admin.command("ping")
	return client


def load_era5_batch_cache(cache_key: str) -> list[dict] | None:
	"""Read a previously downloaded API batch from the shared MongoDB cache."""
	client = connect_era5_mongodb()
	if client is None:
		return None

	document = client["ind320"]["era5_api_batches"].find_one(
		{"_id": cache_key},
		{"compressed_locations": 1},
	)
	if document is None:
		return None
	return json.loads(gzip.decompress(document["compressed_locations"]))


def save_era5_batch_cache(cache_key: str, locations: list[dict]) -> None:
	"""Persist an API response batch so app instances can resume together."""
	client = connect_era5_mongodb()
	if client is None:
		return

	compressed_locations = gzip.compress(
		json.dumps(locations, separators=(",", ":")).encode("utf-8")
	)
	client["ind320"]["era5_api_batches"].replace_one(
		{"_id": cache_key},
		{"_id": cache_key, "compressed_locations": compressed_locations},
		upsert=True,
	)


def reserve_era5_api_budget(
	estimated_calls: float,
	daily_budget: int,
	daily_window_seconds: int,
	hourly_budget: int,
	hourly_window_seconds: int,
) -> tuple[bool, int, int, str | None, str | None] | None:
	"""Reserve estimated API usage across app instances using a MongoDB lease."""
	client = connect_era5_mongodb()
	if client is None:
		return None

	database = client["ind320"]
	usage = database["era5_api_usage"]
	locks = database["era5_api_usage_locks"]
	owner = uuid4().hex
	lock_id = "rolling-24-hour-budget"
	deadline = monotonic() + 30

	while True:
		now = datetime.now(timezone.utc)
		lock = locks.find_one_and_update(
			{
				"_id": lock_id,
				"$or": [
					{"lease_until": {"$lte": now}},
					{"owner": owner},
				],
			},
			{
				"$set": {
					"owner": owner,
					"lease_until": now + timedelta(seconds=30),
				}
			},
			return_document=ReturnDocument.AFTER,
		)
		if lock is not None:
			break

		try:
			locks.insert_one(
				{
					"_id": lock_id,
					"owner": owner,
					"lease_until": now + timedelta(seconds=30),
				}
			)
			break
		except DuplicateKeyError:
			if monotonic() >= deadline:
				raise TimeoutError(
					"Could not acquire the shared Open-Meteo usage-budget lock."
				)
			sleep(0.1)

	try:
		now = datetime.now(timezone.utc)
		daily_start = now - timedelta(seconds=daily_window_seconds)
		hourly_start = now - timedelta(seconds=hourly_window_seconds)
		usage.delete_many({"requested_at": {"$lt": daily_start}})
		daily_used = sum(
			document["estimated_calls"]
			for document in usage.find(
				{"requested_at": {"$gte": daily_start}},
				{"estimated_calls": 1},
			)
		)
		hourly_used = sum(
			document["estimated_calls"]
			for document in usage.find(
				{"requested_at": {"$gte": hourly_start}},
				{"estimated_calls": 1},
			)
		)
		if hourly_used + estimated_calls > hourly_budget:
			return False, daily_used, hourly_used, "hour", None
		if daily_used + estimated_calls > daily_budget:
			return False, daily_used, hourly_used, "day", None

		reservation_id = uuid4().hex
		usage.insert_one(
			{
				"_id": reservation_id,
				"requested_at": now,
				"estimated_calls": estimated_calls,
			}
		)
		return True, daily_used, hourly_used, None, reservation_id
	finally:
		locks.delete_one({"_id": lock_id, "owner": owner})


def release_era5_api_budget(reservation_id: str) -> None:
	"""Release a reserved estimate when an API response proves it was rejected."""
	client = connect_era5_mongodb()
	if client is not None:
		client["ind320"]["era5_api_usage"].delete_one(
			{"_id": reservation_id}
		)


def load_era5_weather_cache(
	area_number: int,
	year: int,
	samples_per_region: int,
	random_seed: int,
) -> pd.DataFrame | None:
	"""Load a complete area/year series from the shared MongoDB cache."""
	client = connect_era5_mongodb()
	if client is None:
		return None

	cache_key = (
		f"NO{area_number}-{year}-ERA5-{samples_per_region}-{random_seed}"
	)
	document = client["ind320"]["era5_weather"].find_one(
		{"_id": cache_key},
		{"records": 1},
	)
	if document is None:
		return None

	data = pd.DataFrame(document["records"])
	data["time"] = pd.to_datetime(data["time"], utc=True, errors="raise")
	return data


def save_era5_weather_cache(
	area_number: int,
	year: int,
	samples_per_region: int,
	random_seed: int,
	data: pd.DataFrame,
) -> None:
	"""Persist a complete area/year weather series in the shared MongoDB cache."""
	client = connect_era5_mongodb()
	if client is None:
		return

	cache_key = (
		f"NO{area_number}-{year}-ERA5-{samples_per_region}-{random_seed}"
	)
	records = data.assign(
		time=pd.to_datetime(data["time"], utc=True).map(
			lambda value: value.isoformat()
		)
	).to_dict(orient="records")
	client["ind320"]["era5_weather"].replace_one(
		{"_id": cache_key},
		{
			"_id": cache_key,
			"area_number": area_number,
			"year": year,
			"model": "ERA5",
			"samples_per_region": samples_per_region,
			"random_seed": random_seed,
			"records": records,
			"cached_at": datetime.now(timezone.utc),
		},
		upsert=True,
	)


def load_monthly_flows() -> pd.DataFrame:
	"""Load processed monthly electricity-flow documents from MongoDB."""
	client = connect_mongodb()
	try:
		documents = list(
			client["ind320"]["monthly_electricity_flows"].find(
				{},
				{"_id": 0},
			)
		)
	finally:
		client.close()

	if not documents:
		raise RuntimeError("MongoDB contains no processed electricity-flow documents.")

	return pd.DataFrame(documents)
