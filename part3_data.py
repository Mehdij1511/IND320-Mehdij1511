import hashlib
import json
import math
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from time import monotonic, sleep, time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point
from mongo_data import (
    load_era5_batch_cache,
    release_era5_api_budget as release_shared_era5_api_budget,
    reserve_era5_api_budget,
    save_era5_batch_cache,
)


PROJECT_ROOT = Path(__file__).resolve().parent
NVE_REGION_FILE = PROJECT_ROOT / "data" / "NVE_shapefiles" / "NVE_Region.shp"
REGION_CODES = ("RM", "RN", "RS", "RV", "RØ")
# The assignment groups East as RS+RØ and North as RM+RN.
REGION_IDENTIFIER_MAP = {
    "NO1": ("RS", "RØ"),
    "NO2": ("RS",),
    "NO3": ("RM",),
    "NO4": ("RM", "RN"),
    "NO5": ("RV",),
}
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ERA5_GRID_DEGREES = 0.25
OPEN_METEO_BATCH_SIZE = 100
OPEN_METEO_REQUEST_INTERVAL = 110.0
OPEN_METEO_HOURLY_CALL_BUDGET = 4500
OPEN_METEO_DAILY_CALL_BUDGET = 9500
OPEN_METEO_HOURLY_WINDOW_SECONDS = 60 * 60
OPEN_METEO_CALL_WINDOW_SECONDS = 24 * 60 * 60
ERA5_CACHE_DIR = PROJECT_ROOT / "data" / "era5_cache"


class Era5ApiBudgetExceeded(RuntimeError):
    """Raised when a request must pause to protect the API quota."""


def load_nve_regions(
    shapefile: Path = NVE_REGION_FILE,
) -> gpd.GeoDataFrame:
    """Load the NVE region polygons in their original coordinate system."""
    regions = gpd.read_file(shapefile, encoding="utf-8")
    required_columns = {"REGION", "REGIONNAVN", "geometry"}
    missing_columns = required_columns.difference(regions.columns)
    if missing_columns:
        raise ValueError(
            f"The NVE shapefile is missing columns: {sorted(missing_columns)}"
        )
    if regions.crs is None:
        raise ValueError("The NVE shapefile does not define a coordinate system.")

    regions = regions.set_index("REGION", drop=False)
    if regions.index.has_duplicates:
        raise ValueError("The NVE shapefile contains duplicate region codes.")

    missing_regions = set(REGION_CODES).difference(regions.index)
    if missing_regions:
        raise ValueError(
            f"The NVE shapefile is missing regions: {sorted(missing_regions)}"
        )

    return regions.loc[list(REGION_CODES)].copy()


def sample_region_locations(
    regions: gpd.GeoDataFrame,
    samples_per_region: int = 1000,
    random_seed: int = 42,
) -> dict[str, list[tuple[float, float]]]:
    """Sample points inside each region and return longitude-latitude pairs."""
    if samples_per_region < 1:
        raise ValueError("samples_per_region must be greater than zero.")
    if regions.crs is None:
        raise ValueError("The region polygons do not define a coordinate system.")
    if not regions.crs.is_projected:
        raise ValueError("Sample locations require a projected coordinate system.")

    random = np.random.default_rng(random_seed)
    coordinates = {}

    for region_code in REGION_CODES:
        if region_code not in regions.index:
            raise ValueError(f"Region {region_code} is not available.")

        geometry = regions.loc[region_code, "geometry"]
        if geometry is None or geometry.is_empty or geometry.area <= 0:
            raise ValueError(f"Region {region_code} has no usable polygon area.")

        min_x, min_y, max_x, max_y = geometry.bounds
        points = []
        attempts = 0
        max_attempts = samples_per_region * 1000

        while len(points) < samples_per_region and attempts < max_attempts:
            remaining = samples_per_region - len(points)
            batch_size = max(remaining * 2, 100)
            xs = random.uniform(min_x, max_x, batch_size)
            ys = random.uniform(min_y, max_y, batch_size)
            points.extend(
                Point(x, y)
                for x, y in zip(xs, ys)
                if geometry.covers(Point(x, y))
            )
            attempts += batch_size

        if len(points) < samples_per_region:
            raise RuntimeError(
                f"Could not sample {samples_per_region} locations in {region_code}."
            )

        point_series = gpd.GeoSeries(
            points[:samples_per_region], crs=regions.crs
        ).to_crs("EPSG:4326")
        coordinates[region_code] = [
            (float(point.x), float(point.y)) for point in point_series
        ]

    return coordinates


def _reserve_era5_call_budget(payload: dict) -> tuple[str, int | str]:
    """Reserve a conservative API-call estimate for the next uncached batch."""
    location_count = len(payload["latitude"])
    start = pd.Timestamp(payload["start_date"]).normalize()
    end = pd.Timestamp(payload["end_date"]).normalize()
    days = (end - start).days + 1
    variable_count = len(payload["hourly"].split(","))
    estimated_calls = (
        location_count
        * math.ceil(days / 14)
        * max(1, variable_count / 10)
    )

    shared_reservation = reserve_era5_api_budget(
        estimated_calls,
        OPEN_METEO_DAILY_CALL_BUDGET,
        OPEN_METEO_CALL_WINDOW_SECONDS,
        OPEN_METEO_HOURLY_CALL_BUDGET,
        OPEN_METEO_HOURLY_WINDOW_SECONDS,
    )
    if shared_reservation is not None:
        reserved, daily_used, hourly_used, limited_window, reservation_id = (
            shared_reservation
        )
        if not reserved:
            window_label = "hour" if limited_window == "hour" else "24-hour"
            used_calls = hourly_used if limited_window == "hour" else daily_used
            limit = (
                OPEN_METEO_HOURLY_CALL_BUDGET
                if limited_window == "hour"
                else OPEN_METEO_DAILY_CALL_BUDGET
            )
            raise Era5ApiBudgetExceeded(
                f"The conservative Open-Meteo budget for the rolling {window_label} "
                f"window is nearly used ({used_calls:,.0f}/{limit:,} estimated "
                f"calls; next batch needs {estimated_calls:,.0f}). Completed "
                "batches are cached. Retry after enough of the rolling window "
                "has elapsed."
            )
        return "mongo", reservation_id

    budget_file = ERA5_CACHE_DIR / "api_usage.sqlite3"
    budget_file.parent.mkdir(parents=True, exist_ok=True)
    now = time()
    window_start = now - OPEN_METEO_CALL_WINDOW_SECONDS

    with closing(sqlite3.connect(budget_file, timeout=30)) as connection:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS api_usage "
                "(requested_at REAL NOT NULL, estimated_calls REAL NOT NULL)"
            )
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM api_usage WHERE requested_at < ?",
                (window_start,),
            )
            used_calls = connection.execute(
                "SELECT COALESCE(SUM(estimated_calls), 0) FROM api_usage"
            ).fetchone()[0]
            hourly_used = connection.execute(
                "SELECT COALESCE(SUM(estimated_calls), 0) FROM api_usage "
                "WHERE requested_at >= ?",
                (now - OPEN_METEO_HOURLY_WINDOW_SECONDS,),
            ).fetchone()[0]
            if hourly_used + estimated_calls > OPEN_METEO_HOURLY_CALL_BUDGET:
                raise Era5ApiBudgetExceeded(
                    "The conservative Open-Meteo budget for the rolling hour is "
                    f"nearly used ({hourly_used:,.0f}/"
                    f"{OPEN_METEO_HOURLY_CALL_BUDGET:,} estimated calls; next "
                    f"batch needs {estimated_calls:,.0f}). Completed batches are "
                    "cached. Retry after enough of the rolling hour has elapsed."
                )
            if used_calls + estimated_calls > OPEN_METEO_DAILY_CALL_BUDGET:
                raise Era5ApiBudgetExceeded(
                    "The conservative Open-Meteo request budget for the last 24 "
                    f"hours is nearly used "
                    f"({used_calls:,.0f}/{OPEN_METEO_DAILY_CALL_BUDGET:,} "
                    f"estimated calls; next batch needs {estimated_calls:,.0f}). "
                    "Completed batches are cached. Retry after enough of the "
                    "rolling 24-hour window has elapsed."
                )
            reservation = connection.execute(
                "INSERT INTO api_usage (requested_at, estimated_calls) "
                "VALUES (?, ?)",
                (now, estimated_calls),
            )
    return "sqlite", reservation.lastrowid


def _release_era5_call_budget(reservation: tuple[str, int | str]) -> None:
    """Release a call estimate when Open-Meteo explicitly rejects a request."""
    backend, reservation_id = reservation
    if backend == "mongo":
        release_shared_era5_api_budget(str(reservation_id))
        return
    if backend == "sqlite":
        budget_file = ERA5_CACHE_DIR / "api_usage.sqlite3"
        with closing(sqlite3.connect(budget_file, timeout=30)) as connection:
            with connection:
                connection.execute(
                    "DELETE FROM api_usage WHERE rowid = ?",
                    (reservation_id,),
                )
        return
    raise ValueError(f"Unknown API budget backend: {backend!r}")


def _request_era5_batch(payload: dict, cache_dir: Path) -> list[dict]:
    """Load a completed API batch from disk or fetch and cache it."""
    cache_key = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.is_file():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    locations = load_era5_batch_cache(cache_key)
    if locations is not None:
        temporary_file = cache_file.with_suffix(".tmp")
        temporary_file.write_text(json.dumps(locations), encoding="utf-8")
        temporary_file.replace(cache_file)
        return locations

    reservation = _reserve_era5_call_budget(payload)
    response = requests.post(
        OPEN_METEO_ARCHIVE_URL,
        json=payload,
        timeout=(15, 180),
    )
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        response_detail = response.text.strip()[:200]
        retry_message = (
            f" Retry-After: {retry_after}." if retry_after else ""
        )
        if "daily api request limit" in response_detail.lower():
            _release_era5_call_budget(reservation)
            raise Era5ApiBudgetExceeded(
                "Open-Meteo reported that its daily API limit has been reached. "
                f"Completed batches are cached.{retry_message} Retry manually "
                "after the limit resets."
            )
        _release_era5_call_budget(reservation)
        detail_message = (
            f" Server response: {response_detail}" if response_detail else ""
        )
        raise Era5ApiBudgetExceeded(
            "Open-Meteo rate-limited this request (HTTP 429). No automatic "
            "retry was made to protect your quota."
            f"{retry_message}{detail_message} Completed batches are cached; "
            "retry manually after the rate-limit window has elapsed."
        )
    if not response.ok:
        if 400 <= response.status_code < 500:
            _release_era5_call_budget(reservation)
        raise requests.HTTPError(
            f"Open-Meteo returned HTTP {response.status_code}: {response.text}",
            response=response,
        )

    locations = response.json()
    if isinstance(locations, dict):
        locations = [locations]
    temporary_file = cache_file.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(locations), encoding="utf-8")
    temporary_file.replace(cache_file)
    save_era5_batch_cache(cache_key, locations)
    return locations


def _coordinate_key(longitude: float, latitude: float) -> tuple[float, float]:
    return round(float(longitude), 6), round(float(latitude), 6)


def _load_cached_era5_locations(
    cache_dir: Path,
    coordinates: list[tuple[float, float]],
    expected_times: pd.DatetimeIndex,
) -> dict[tuple[float, float], dict]:
    """Reuse locations from cached batches even when their batch sizes differ."""
    requested = {_coordinate_key(*coordinate) for coordinate in coordinates}
    cached_locations = {}
    conflicting_locations = set()

    for cache_file in cache_dir.glob("*.json"):
        locations = json.loads(cache_file.read_text(encoding="utf-8"))
        if not isinstance(locations, list):
            raise ValueError(f"Cached ERA5 batch is not a location list: {cache_file}")

        for location in locations:
            if not isinstance(location, dict):
                raise ValueError(f"Cached ERA5 location is invalid: {cache_file}")
            if "longitude" not in location or "latitude" not in location:
                raise ValueError(f"Cached ERA5 location has no coordinates: {cache_file}")
            key = _coordinate_key(location["longitude"], location["latitude"])
            if key not in requested or key in conflicting_locations:
                continue

            hourly = location.get("hourly")
            if not isinstance(hourly, dict) or "time" not in hourly:
                continue
            timestamps = hourly["time"]
            if not isinstance(timestamps, list) or len(timestamps) != len(expected_times):
                continue
            if (
                timestamps[0] != expected_times[0].strftime("%Y-%m-%dT%H:%M")
                or timestamps[-1] != expected_times[-1].strftime("%Y-%m-%dT%H:%M")
            ):
                continue
            returned_times = pd.DatetimeIndex(
                pd.to_datetime(timestamps, utc=True, errors="raise")
            )
            if not returned_times.equals(expected_times):
                continue

            precipitation_key = (
                "precipitation_era5"
                if "precipitation_era5" in hourly
                else "precipitation"
            )
            temperature_key = (
                "temperature_2m_era5"
                if "temperature_2m_era5" in hourly
                else "temperature_2m"
            )
            if precipitation_key not in hourly or temperature_key not in hourly:
                raise ValueError(
                    f"Cached ERA5 location lacks precipitation or temperature: {cache_file}"
                )
            precipitation = np.asarray(hourly[precipitation_key], dtype=float)
            temperature = np.asarray(hourly[temperature_key], dtype=float)
            if precipitation.shape != (len(expected_times),) or temperature.shape != (
                len(expected_times),
            ):
                raise ValueError(
                    f"Cached ERA5 location has incomplete hourly values: {cache_file}"
                )

            if key in cached_locations:
                existing = cached_locations[key]["hourly"]
                existing_precipitation = np.asarray(
                    existing.get("precipitation_era5", existing.get("precipitation")),
                    dtype=float,
                )
                existing_temperature = np.asarray(
                    existing.get(
                        "temperature_2m_era5", existing.get("temperature_2m")
                    ),
                    dtype=float,
                )
                if not (
                    np.array_equal(precipitation, existing_precipitation, equal_nan=True)
                    and np.array_equal(temperature, existing_temperature, equal_nan=True)
                ):
                    cached_locations.pop(key)
                    conflicting_locations.add(key)
                continue
            cached_locations[key] = location

    return cached_locations


def _download_era5_locations(
    coordinates: list[tuple[float, float]],
    start_date: str,
    end_date: str,
    batch_size: int = OPEN_METEO_BATCH_SIZE,
    location_weights: list[int] | None = None,
) -> pd.DataFrame:
    """Download yearly ERA5 batches and return their weighted hourly mean."""
    if not coordinates:
        raise ValueError("At least one coordinate pair is required.")
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")
    if location_weights is None:
        location_weights = [1] * len(coordinates)
    if len(location_weights) != len(coordinates) or any(
        weight < 1 for weight in location_weights
    ):
        raise ValueError("Each coordinate must have a positive integer weight.")

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.tz is not None:
        start = start.tz_convert("UTC").tz_localize(None)
    if end.tz is not None:
        end = end.tz_convert("UTC").tz_localize(None)
    start = start.normalize()
    end = end.normalize()
    if start > end:
        raise ValueError("start_date must be on or before end_date.")

    cache_dir = ERA5_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    if any(
        not np.isfinite(longitude)
        or not np.isfinite(latitude)
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
        for longitude, latitude in coordinates
    ):
        raise ValueError("Coordinate pairs must contain valid longitude and latitude.")

    last_request_started = None
    interval_results = []
    interval_start = start

    while interval_start <= end:
        year_end = pd.Timestamp(year=interval_start.year, month=12, day=31)
        interval_end = min(year_end, end)
        expected_times = pd.date_range(
            start=interval_start,
            end=interval_end + pd.Timedelta(days=1),
            freq="h",
            inclusive="left",
            tz="UTC",
        )
        location_data = _load_cached_era5_locations(
            cache_dir,
            coordinates,
            expected_times,
        )
        unique_coordinates = {}
        for coordinate in coordinates:
            unique_coordinates.setdefault(_coordinate_key(*coordinate), coordinate)
        missing_coordinates = [
            coordinate
            for key, coordinate in unique_coordinates.items()
            if key not in location_data
        ]

        for offset in range(0, len(missing_coordinates), batch_size):
            batch = missing_coordinates[offset : offset + batch_size]
            location_count = len(batch)
            payload = {
                "latitude": [latitude for longitude, latitude in batch],
                "longitude": [longitude for longitude, latitude in batch],
                "start_date": interval_start.strftime("%Y-%m-%d"),
                "end_date": interval_end.strftime("%Y-%m-%d"),
                "hourly": "precipitation,temperature_2m",
                "models": "era5",
                "timezone": "UTC",
            }
            cache_key = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            cached = (cache_dir / f"{cache_key}.json").is_file()
            if not cached and last_request_started is not None:
                wait = OPEN_METEO_REQUEST_INTERVAL - (
                    monotonic() - last_request_started
                )
                if wait > 0:
                    sleep(wait)

            if not cached:
                last_request_started = monotonic()
            locations = _request_era5_batch(payload, cache_dir)
            if len(locations) != location_count:
                raise ValueError(
                    "Open-Meteo returned a different number of locations "
                    f"({len(locations)}) than requested ({location_count})."
                )

            batch_times = None
            for location, coordinate in zip(locations, batch):
                hourly = location.get("hourly")
                if not isinstance(hourly, dict) or "time" not in hourly:
                    raise ValueError("Open-Meteo response is missing hourly time data.")
                if batch_times is None:
                    batch_times = hourly["time"]
                elif hourly["time"] != batch_times:
                    raise ValueError("Open-Meteo returned mismatched hourly timestamps.")

                precipitation_key = (
                    "precipitation_era5"
                    if "precipitation_era5" in hourly
                    else "precipitation"
                )
                temperature_key = (
                    "temperature_2m_era5"
                    if "temperature_2m_era5" in hourly
                    else "temperature_2m"
                )
                if precipitation_key not in hourly or temperature_key not in hourly:
                    raise ValueError(
                        "Open-Meteo response is missing ERA5 precipitation or temperature."
                    )
                returned_times = pd.DatetimeIndex(
                    pd.to_datetime(hourly["time"], utc=True, errors="raise")
                )
                if not returned_times.equals(expected_times):
                    raise ValueError(
                        "Open-Meteo did not return every expected hourly timestamp "
                        "for the requested interval."
                    )
                if len(hourly[precipitation_key]) != len(expected_times) or len(
                    hourly[temperature_key]
                ) != len(expected_times):
                    raise ValueError(
                        "Open-Meteo returned an incomplete hourly time series."
                    )
                location_data[_coordinate_key(*coordinate)] = location

        precipitation_values = []
        temperature_values = []
        for coordinate in coordinates:
            location = location_data[_coordinate_key(*coordinate)]
            hourly = location["hourly"]
            precipitation_key = (
                "precipitation_era5"
                if "precipitation_era5" in hourly
                else "precipitation"
            )
            temperature_key = (
                "temperature_2m_era5"
                if "temperature_2m_era5" in hourly
                else "temperature_2m"
            )
            precipitation_values.append(hourly[precipitation_key])
            temperature_values.append(hourly[temperature_key])

        precipitation_array = np.asarray(precipitation_values, dtype=float)
        temperature_array = np.asarray(temperature_values, dtype=float)
        if (
            precipitation_array.shape[1] != len(expected_times)
            or temperature_array.shape[1] != len(expected_times)
        ):
            raise ValueError("Open-Meteo returned an incomplete hourly time series.")

        batch_weights = np.asarray(location_weights, dtype=int)[:, np.newaxis]
        interval_precipitation = np.nansum(
            precipitation_array * batch_weights, axis=0
        )
        interval_temperature = np.nansum(
            temperature_array * batch_weights, axis=0
        )
        precipitation_counts = (
            np.isfinite(precipitation_array) * batch_weights
        ).sum(axis=0)
        temperature_counts = (
            np.isfinite(temperature_array) * batch_weights
        ).sum(axis=0)

        if np.any(precipitation_counts == 0) or np.any(temperature_counts == 0):
            raise ValueError("Open-Meteo returned no valid data for one or more hours.")

        interval_results.append(
            pd.DataFrame(
                {
                    "time": expected_times,
                    "precipitation": interval_precipitation / precipitation_counts,
                    "temperature_2m": interval_temperature / temperature_counts,
                }
            )
        )
        interval_start = interval_end + pd.Timedelta(days=1)

    return pd.concat(interval_results, ignore_index=True)


def download_era5_data(
    region_identifier: str,
    start_date: str,
    end_date: str,
    samples_per_region: int = 1000,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Load or download a cached hourly ERA5 mean for a region and interval."""
    if region_identifier in REGION_IDENTIFIER_MAP:
        region_codes = REGION_IDENTIFIER_MAP[region_identifier]
    elif region_identifier in REGION_CODES:
        region_codes = (region_identifier,)
    else:
        supported = sorted((*REGION_CODES, *REGION_IDENTIFIER_MAP))
        raise ValueError(
            f"Unsupported region identifier {region_identifier!r}. "
            f"Choose one of: {supported}."
        )

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.tz is not None:
        start = start.tz_convert("UTC").tz_localize(None)
    if end.tz is not None:
        end = end.tz_convert("UTC").tz_localize(None)
    start = start.normalize()
    end = end.normalize()
    if start > end:
        raise ValueError("start_date must be on or before end_date.")

    cache_key = hashlib.sha256(
        json.dumps(
            {
                "regions": region_codes,
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "samples_per_region": samples_per_region,
                "random_seed": random_seed,
                "model": "era5",
                "grid_degrees": ERA5_GRID_DEGREES,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    series_cache = ERA5_CACHE_DIR / "series" / f"{cache_key}.csv"
    expected_times = pd.date_range(
        start=start,
        end=end + pd.Timedelta(days=1),
        freq="h",
        inclusive="left",
        tz="UTC",
    )
    if series_cache.is_file():
        data = pd.read_csv(series_cache)
        data["time"] = pd.to_datetime(data["time"], utc=True, errors="raise")
        if (
            list(data.columns) != ["time", "precipitation", "temperature_2m"]
            or not pd.DatetimeIndex(data["time"]).equals(expected_times)
            or not data[["precipitation", "temperature_2m"]].notna().all().all()
        ):
            raise ValueError(
                f"The cached ERA5 series is incomplete or invalid: {series_cache}"
            )
        return data

    regions = load_nve_regions()
    coordinates_by_region = sample_region_locations(
        regions,
        samples_per_region=samples_per_region,
        random_seed=random_seed,
    )
    coordinates = [
        point
        for region_code in region_codes
        for point in coordinates_by_region[region_code]
    ]
    grid_weights = Counter(
        (
            round(longitude / ERA5_GRID_DEGREES) * ERA5_GRID_DEGREES,
            round(latitude / ERA5_GRID_DEGREES) * ERA5_GRID_DEGREES,
        )
        for longitude, latitude in coordinates
    )
    grid_coordinates = list(grid_weights)
    data = _download_era5_locations(
        grid_coordinates,
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        location_weights=list(grid_weights.values()),
    )
    if (
        not pd.DatetimeIndex(data["time"]).equals(expected_times)
        or not data[["precipitation", "temperature_2m"]].notna().all().all()
    ):
        raise ValueError(
            "The ERA5 area series is incomplete; it will not be cached as complete."
        )

    series_cache.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = series_cache.with_suffix(".tmp")
    data.to_csv(temporary_file, index=False)
    temporary_file.replace(series_cache)
    return data
