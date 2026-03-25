import os
import time
import requests
import pandas as pd

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

class FredClient:
    def __init__(self, api_key: str | None = None, cache_seconds: int = 900):
        self.api_key = api_key or os.getenv("FRED_API_KEY")
        self.cache_seconds = cache_seconds
        self._cache: dict[tuple[str,str,str], tuple[float, pd.DataFrame]] = {}

    def get_series(self, series_id: str, observation_start: str = "", observation_end: str = "") -> pd.DataFrame:
        if not self.api_key:
            raise RuntimeError("FRED_API_KEY is missing. Set it as an environment variable.")

        cache_key = (series_id, observation_start, observation_end)
        now = time.time()
        if cache_key in self._cache:
            ts, df = self._cache[cache_key]
            if now - ts < self.cache_seconds:
                return df.copy()

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
        }
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end

        r = requests.get(FRED_BASE, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        obs = payload.get("observations", [])
        df = pd.DataFrame(obs)
        if df.empty:
            return df
        df = df[["date", "value"]].copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().sort_values("date")
        self._cache[cache_key] = (now, df)
        return df.copy()
