"""Dataset Construction, Chronological Splits, and Sequence Windows.

Combines:
1. Chronological walk-forward validation splitting
2. Multi-horizon sequence window generation (Lookback L=14, Forecast H=5)
3. Full dataset serialization to Parquet and NPZ formats
"""

from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import pandas as pd

from features.feature_pipeline import UnifiedFeaturePipeline


class ChronologicalSplitter:
    """Performs strict time-based splits on panel data."""

    def __init__(self, time_col: str = "date", val_ratio: float = 0.15, test_ratio: float = 0.15):
        self.time_col = time_col
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        unique_times = sorted(df[self.time_col].unique())
        n_times = len(unique_times)
        n_test = max(1, int(n_times * self.test_ratio))
        n_val = max(1, int(n_times * self.val_ratio))
        n_train = n_times - n_test - n_val

        train_cutoff = unique_times[n_train - 1]
        val_cutoff = unique_times[n_train + n_val - 1]

        df_train = df[df[self.time_col] <= train_cutoff].copy()
        df_val = df[(df[self.time_col] > train_cutoff) & (df[self.time_col] <= val_cutoff)].copy()
        df_test = df[df[self.time_col] > val_cutoff].copy()
        return df_train, df_val, df_test


class MultiHorizonSequenceBuilder:
    """Builds sliding sequence windows for multi-horizon temporal models."""

    def __init__(
        self,
        lookback_days: int = 14,
        forecast_horizon_days: int = 5,
        target_col: str = "emergency_hospitalizations",
        past_weather_cols: Optional[List[str]] = None,
        future_weather_cols: Optional[List[str]] = None,
        static_cols: Optional[List[str]] = None,
    ):
        self.lookback_days = lookback_days
        self.forecast_horizon_days = forecast_horizon_days
        self.target_col = target_col
        self.past_weather_cols = past_weather_cols or ["peak_temperature_c", "min_night_temp_c", "peak_wbgt_c"]
        self.future_weather_cols = future_weather_cols or ["peak_temperature_c", "min_night_temp_c", "peak_wbgt_c"]
        self.static_cols = static_cols or ["population_density", "elderly_percentage", "outdoor_worker_density", "slum_percentage"]

    def build_sequences(
        self, df: pd.DataFrame, group_col: str = "ward_id", time_col: str = "date"
    ) -> Dict[str, np.ndarray]:
        X_past, X_future, X_static, y, dates, ward_ids = [], [], [], [], [], []
        p_cols = [c for c in self.past_weather_cols if c in df.columns]
        f_cols = [c for c in self.future_weather_cols if c in df.columns]
        s_cols = [c for c in self.static_cols if c in df.columns]

        df_sorted = df.sort_values([group_col, time_col]).copy()
        total_window = self.lookback_days + self.forecast_horizon_days

        for w_id, group in df_sorted.groupby(group_col):
            group = group.reset_index(drop=True)
            n_rows = len(group)
            if n_rows < total_window:
                continue

            static_vals = group[s_cols].iloc[0].fillna(0.0).values.astype(np.float32)
            past_mat = group[p_cols].ffill().fillna(0.0).values.astype(np.float32)
            future_mat = group[f_cols].ffill().fillna(0.0).values.astype(np.float32)
            target_series = group[self.target_col].values.astype(np.float32) if self.target_col in group.columns else np.zeros(n_rows, dtype=np.float32)

            for i in range(n_rows - total_window + 1):
                tgt_window = target_series[i + self.lookback_days : i + total_window]
                if np.isnan(tgt_window).any():
                    continue

                X_past.append(past_mat[i : i + self.lookback_days])
                X_future.append(future_mat[i + self.lookback_days : i + total_window])
                X_static.append(static_vals)
                y.append(tgt_window)
                dates.append(str(group[time_col].iloc[i + self.lookback_days]))
                ward_ids.append(w_id)

        if len(X_past) == 0:
            return {
                "X_past": np.empty((0, self.lookback_days, len(p_cols))),
                "X_future": np.empty((0, self.forecast_horizon_days, len(f_cols))),
                "X_static": np.empty((0, len(s_cols))),
                "y": np.empty((0, self.forecast_horizon_days)),
                "prediction_dates": np.array([]),
            }

        return {
            "X_past": np.array(X_past, dtype=np.float32),
            "X_future": np.array(X_future, dtype=np.float32),
            "X_static": np.array(X_static, dtype=np.float32),
            "y": np.array(y, dtype=np.float32),
            "prediction_dates": np.array(dates),
        }


class DatasetBuilder:
    """Coordinates full dataset assembly, split, and storage."""

    def __init__(self, output_dir: str = "data/features"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = UnifiedFeaturePipeline()
        self.splitter = ChronologicalSplitter()
        self.seq_builder = MultiHorizonSequenceBuilder()

    def build_and_save(
        self,
        df_weather_hourly: pd.DataFrame,
        df_spatial_features: pd.DataFrame,
        df_health_daily: Optional[pd.DataFrame] = None,
        prefix: str = "unified_dataset",
    ) -> Dict[str, Any]:
        df_unified = self.pipeline.assemble_ward_time_features(
            df_weather_hourly, df_spatial_features, df_health_daily
        )
        df_train, df_val, df_test = self.splitter.split(df_unified)

        train_path = self.output_dir / f"{prefix}_train.parquet"
        val_path = self.output_dir / f"{prefix}_val.parquet"
        test_path = self.output_dir / f"{prefix}_test.parquet"

        df_train.to_parquet(train_path, index=False)
        df_val.to_parquet(val_path, index=False)
        df_test.to_parquet(test_path, index=False)

        # Build Multi-Horizon Sequence Arrays from continuous panel
        seq_all = self.seq_builder.build_sequences(df_unified)
        pred_dates = pd.to_datetime(seq_all["prediction_dates"]).date

        train_cutoff = df_train["date"].max()
        val_cutoff = df_val["date"].max()

        train_mask = pred_dates <= train_cutoff
        val_mask = (pred_dates > train_cutoff) & (pred_dates <= val_cutoff)
        test_mask = pred_dates > val_cutoff

        seq_path = self.output_dir / f"{prefix}_sequences.npz"
        np.savez_compressed(
            seq_path,
            X_train_past=seq_all["X_past"][train_mask],
            X_train_future=seq_all["X_future"][train_mask],
            X_train_static=seq_all["X_static"][train_mask],
            y_train=seq_all["y"][train_mask],
            X_val_past=seq_all["X_past"][val_mask],
            X_val_future=seq_all["X_future"][val_mask],
            X_val_static=seq_all["X_static"][val_mask],
            y_val=seq_all["y"][val_mask],
            X_test_past=seq_all["X_past"][test_mask],
            X_test_future=seq_all["X_future"][test_mask],
            X_test_static=seq_all["X_static"][test_mask],
            y_test=seq_all["y"][test_mask],
        )

        return {
            "tabular_train_path": str(train_path),
            "train_rows": len(df_train),
            "val_rows": len(df_val),
            "test_rows": len(df_test),
        }
