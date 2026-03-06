"""Fama-French factor model — download, parse, and estimate exposures."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm

from config import FRENCH_DATA_DIR
from schemas.portfolio import FactorExposure

FF3_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip"
FF5_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"


class FamaFrenchModel:
    def __init__(self) -> None:
        self._ff3_cache: Optional[pd.DataFrame] = None
        self._ff5_cache: Optional[pd.DataFrame] = None

    def _download_and_parse(self, url: str, n_factors: int) -> pd.DataFrame:
        cache_file = FRENCH_DATA_DIR / f"ff{n_factors}_daily.csv"
        if cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if len(df) > 100:
                return df

        resp = requests.get(url, timeout=60)
        resp.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
            raw = zf.read(csv_name).decode("utf-8")

        lines = raw.strip().split("\n")
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip() and line.strip()[0].isdigit():
                start_idx = i
                break

        data_lines = []
        for line in lines[start_idx:]:
            stripped = line.strip()
            if not stripped or not stripped[0].isdigit():
                break
            data_lines.append(stripped)

        df = pd.read_csv(
            io.StringIO("\n".join(data_lines)),
            header=None,
        )

        if n_factors == 3:
            if df.shape[1] >= 5:
                df.columns = ["date", "Mkt-RF", "SMB", "HML", "RF"][:df.shape[1]]
            else:
                df.columns = [f"col{i}" for i in range(df.shape[1])]
        else:
            if df.shape[1] >= 7:
                df.columns = ["date", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"][:df.shape[1]]
            else:
                df.columns = [f"col{i}" for i in range(df.shape[1])]

        df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d", errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.set_index("date")

        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0

        df.to_csv(cache_file)
        return df

    def get_ff3(self) -> pd.DataFrame:
        if self._ff3_cache is None:
            self._ff3_cache = self._download_and_parse(FF3_URL, 3)
        return self._ff3_cache

    def get_ff5(self) -> pd.DataFrame:
        if self._ff5_cache is None:
            self._ff5_cache = self._download_and_parse(FF5_URL, 5)
        return self._ff5_cache

    def estimate_exposure(
        self,
        returns: pd.Series,
        model_type: str = "FF3",
        ticker_or_portfolio: str = "portfolio",
    ) -> FactorExposure:
        ff = self.get_ff3() if model_type == "FF3" else self.get_ff5()

        if model_type == "FF3":
            factor_cols = ["Mkt-RF", "SMB", "HML"]
        else:
            factor_cols = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]

        available_cols = [c for c in factor_cols if c in ff.columns]
        if not available_cols:
            return FactorExposure(
                ticker_or_portfolio=ticker_or_portfolio,
                model_type=model_type,
                interpretation="Factor data unavailable — columns missing.",
            )

        merged = pd.DataFrame({"ret": returns}).join(ff[available_cols + ["RF"]], how="inner")
        merged = merged.dropna()

        if len(merged) < 30:
            return FactorExposure(
                ticker_or_portfolio=ticker_or_portfolio,
                model_type=model_type,
                observations=len(merged),
                interpretation="Insufficient overlapping observations for regression.",
            )

        y = merged["ret"] - merged["RF"]
        X = sm.add_constant(merged[available_cols])
        result = sm.OLS(y, X).fit()

        betas = {col: float(result.params.get(col, 0)) for col in available_cols}
        beta_pvalues = {col: float(result.pvalues.get(col, 1)) for col in available_cols}

        interp_parts = []
        for col in available_cols:
            b = betas[col]
            p = beta_pvalues[col]
            sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
            interp_parts.append(f"{col}: β={b:.3f}{sig}")
        interpretation = "; ".join(interp_parts)
        if result.params.get("const", 0) != 0:
            alpha_ann = float(result.params["const"]) * 252
            interpretation += f" | Annualized α={alpha_ann:.2%}"

        return FactorExposure(
            ticker_or_portfolio=ticker_or_portfolio,
            timestamp=datetime.utcnow(),
            model_type=model_type,
            alpha=float(result.params.get("const", 0)),
            alpha_pvalue=float(result.pvalues.get("const", 1)),
            betas=betas,
            beta_pvalues=beta_pvalues,
            r_squared=float(result.rsquared),
            adj_r_squared=float(result.rsquared_adj),
            observations=len(merged),
            interpretation=interpretation,
        )
