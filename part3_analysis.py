import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL


def _numeric_series(
    data: pd.Series | pd.DataFrame,
    value_column: str,
) -> pd.Series:
    if isinstance(data, pd.DataFrame):
        if value_column not in data.columns:
            raise ValueError(f"Data is missing the {value_column!r} column.")
        if "time" in data.columns:
            series = pd.Series(
                data[value_column].to_numpy(),
                index=pd.to_datetime(data["time"], errors="raise"),
                name=value_column,
            )
        else:
            series = data[value_column].copy()
    elif isinstance(data, pd.Series):
        series = data.copy()
    else:
        raise TypeError("data must be a pandas Series or DataFrame.")

    values = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    if len(values) < 3 or not np.isfinite(values).all():
        raise ValueError("The input must contain at least three finite observations.")
    series = pd.Series(values, index=series.index, name=value_column)
    return series


def plot_precipitation_outliers(
    data: pd.DataFrame,
    frequency_cutoff: int = 52,
    n_standard_deviations: float = 3.0,
) -> tuple[plt.Figure, dict[str, float | int], pd.DataFrame]:
    """Plot precipitation with robust SPC limits estimated from high-pass DCT values."""
    series = _numeric_series(data, "precipitation")
    values = series.to_numpy()
    if not 1 <= frequency_cutoff < len(values):
        raise ValueError("frequency_cutoff must be between 1 and the series length.")
    if n_standard_deviations <= 0:
        raise ValueError("n_standard_deviations must be greater than zero.")

    coefficients = dct(values, type=2, norm="ortho")
    coefficients[:frequency_cutoff] = 0
    satv = idct(coefficients, type=2, norm="ortho")
    center = float(np.median(satv))
    robust_sigma = float(1.4826 * np.median(np.abs(satv - center)))
    if not np.isfinite(robust_sigma) or robust_sigma == 0:
        raise ValueError("Robust SATV variation is zero; SPC limits cannot be estimated.")

    seasonal_baseline = values - satv
    lower_limit = np.maximum(
        0,
        seasonal_baseline + center - n_standard_deviations * robust_sigma,
    )
    upper_limit = seasonal_baseline + center + n_standard_deviations * robust_sigma
    lower_outliers = satv < center - n_standard_deviations * robust_sigma
    upper_outliers = satv > center + n_standard_deviations * robust_sigma
    outlier_mask = lower_outliers | upper_outliers

    figure, axis = plt.subplots(figsize=(12, 5))
    axis.plot(series.index, values, color="#176B87", linewidth=1, label="Precipitation")
    axis.plot(
        series.index,
        lower_limit,
        color="#D97706",
        linestyle="--",
        linewidth=1,
        label="Robust SPC limits",
    )
    axis.plot(
        series.index,
        upper_limit,
        color="#D97706",
        linestyle="--",
        linewidth=1,
    )
    axis.scatter(
        series.index[outlier_mask],
        values[outlier_mask],
        color="#C1121F",
        s=18,
        label="Outlier",
        zorder=3,
    )
    axis.set(title="Hourly precipitation and robust SPC limits", ylabel="Precipitation (mm)")
    axis.legend()
    axis.grid(alpha=0.2)
    figure.tight_layout()

    outliers = pd.DataFrame(
        {
            "time": series.index[outlier_mask],
            "precipitation": values[outlier_mask],
            "lower_limit": lower_limit[outlier_mask],
            "upper_limit": upper_limit[outlier_mask],
            "direction": np.where(upper_outliers[outlier_mask], "high", "low"),
        }
    ).reset_index(drop=True)
    summary = {
        "observations": len(values),
        "outliers": int(outlier_mask.sum()),
        "outlier_percentage": float(100 * outlier_mask.mean()),
        "low_outliers": int(lower_outliers.sum()),
        "high_outliers": int(upper_outliers.sum()),
        "satv_median": center,
        "satv_robust_sigma": robust_sigma,
    }
    return figure, summary, outliers


def plot_temperature_anomalies(
    data: pd.DataFrame,
    contamination: float = 0.01,
) -> tuple[plt.Figure, dict[str, float | int], pd.DataFrame]:
    """Plot temperature and identify anomalies with Local Outlier Factor."""
    series = _numeric_series(data, "temperature_2m")
    values = series.to_numpy()
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be greater than zero and less than 0.5.")

    neighbors = min(20, len(values) - 1)
    detector = LocalOutlierFactor(
        n_neighbors=neighbors,
        contamination=contamination,
    )
    labels = detector.fit_predict(values.reshape(-1, 1))
    anomaly_mask = labels == -1

    figure, axis = plt.subplots(figsize=(12, 5))
    axis.plot(series.index, values, color="#176B87", linewidth=1, label="Temperature")
    axis.scatter(
        series.index[anomaly_mask],
        values[anomaly_mask],
        color="#C1121F",
        s=18,
        label="LOF anomaly",
        zorder=3,
    )
    axis.set(title="Hourly temperature anomalies (Local Outlier Factor)", ylabel="Temperature (°C)")
    axis.legend()
    axis.grid(alpha=0.2)
    figure.tight_layout()

    outliers = pd.DataFrame(
        {
            "time": series.index[anomaly_mask],
            "temperature_2m": values[anomaly_mask],
            "lof_score": detector.negative_outlier_factor_[anomaly_mask],
        }
    ).reset_index(drop=True)
    summary = {
        "observations": len(values),
        "anomalies": int(anomaly_mask.sum()),
        "anomaly_percentage": float(100 * anomaly_mask.mean()),
        "contamination": contamination,
    }
    return figure, summary, outliers


def plot_stl_decomposition(
    data: pd.Series | pd.DataFrame,
    period: int = 52,
    seasonal: int = 13,
    trend: int = 53,
    robust: bool = True,
) -> tuple[plt.Figure, object]:
    """Decompose a weekly reservoir-filling series with STL and plot its components."""
    series = _numeric_series(data, "fyllingsgrad")
    if period < 2:
        raise ValueError("period must be at least two.")
    if seasonal < 7 or seasonal % 2 == 0:
        raise ValueError("seasonal must be an odd integer of at least seven.")
    if trend <= period or trend % 2 == 0:
        raise ValueError("trend must be an odd integer greater than period.")
    if len(series) < 2 * period:
        raise ValueError(f"At least {2 * period} observations are required for STL.")

    decomposition = STL(
        series,
        period=period,
        seasonal=seasonal,
        trend=trend,
        robust=robust,
    ).fit()
    figure, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True)
    components = (
        (decomposition.observed, "Observed"),
        (decomposition.trend, "Trend"),
        (decomposition.seasonal, "Seasonal"),
        (decomposition.resid, "Residual"),
    )
    for axis, (values, label) in zip(axes, components):
        axis.plot(series.index, values, linewidth=1)
        axis.set_ylabel(label)
        axis.grid(alpha=0.2)
    axes[0].set_title("STL decomposition of reservoir filling")
    figure.tight_layout()
    return figure, decomposition


def plot_spectrogram(
    data: pd.Series | pd.DataFrame,
    window_length: int = 64,
    window_overlap: int = 32,
) -> plt.Figure:
    """Plot the spectrogram of a reservoir-filling series."""
    series = _numeric_series(data, "fyllingsgrad")
    if not 2 <= window_length <= len(series):
        raise ValueError("window_length must be between two and the series length.")
    if not 0 <= window_overlap < window_length:
        raise ValueError("window_overlap must be non-negative and less than window_length.")

    frequencies, times, power = spectrogram(
        series.to_numpy(),
        fs=1.0,
        window="hann",
        nperseg=window_length,
        noverlap=window_overlap,
        detrend="constant",
        scaling="density",
        mode="psd",
    )
    if isinstance(series.index, pd.DatetimeIndex) and len(series.index) > 1:
        interval = series.index.to_series().diff().median()
        time_axis = series.index[0] + pd.to_timedelta(
            times * interval.total_seconds(),
            unit="s",
        )
        x_label = "Date"
    else:
        time_axis = times
        x_label = "Samples from start"

    figure, axis = plt.subplots(figsize=(12, 5))
    mesh = axis.pcolormesh(
        time_axis,
        frequencies,
        10 * np.log10(power + np.finfo(float).tiny),
        shading="auto",
        cmap="magma",
    )
    figure.colorbar(mesh, ax=axis, label="Power spectral density (dB)")
    axis.set(
        title="Spectrogram of reservoir filling",
        xlabel=x_label,
        ylabel="Frequency (cycles per observation)",
    )
    figure.tight_layout()
    return figure
