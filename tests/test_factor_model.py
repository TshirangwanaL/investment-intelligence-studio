"""Tests for the factor model (Fama-French) module."""

import pytest
import numpy as np
import pandas as pd

from quant.factor_model import FamaFrenchModel
from schemas.portfolio import FactorExposure


class TestFamaFrenchParsing:
    def test_estimate_with_synthetic_data(self):
        """Test factor regression using synthetic returns (no download needed)."""
        np.random.seed(42)
        n = 252

        mkt = np.random.normal(0.0004, 0.01, n)
        smb = np.random.normal(0.0001, 0.005, n)
        hml = np.random.normal(0.0001, 0.005, n)
        rf = np.full(n, 0.04 / 252)

        true_alpha = 0.0002
        true_betas = {"Mkt-RF": 1.1, "SMB": 0.3, "HML": -0.2}
        noise = np.random.normal(0, 0.003, n)

        port_ret = (
            rf
            + true_betas["Mkt-RF"] * mkt
            + true_betas["SMB"] * smb
            + true_betas["HML"] * hml
            + true_alpha
            + noise
        )

        dates = pd.date_range("2023-01-01", periods=n, freq="B")
        ff_df = pd.DataFrame({
            "Mkt-RF": mkt,
            "SMB": smb,
            "HML": hml,
            "RF": rf,
        }, index=dates)

        model = FamaFrenchModel()
        model._ff3_cache = ff_df

        returns = pd.Series(port_ret, index=dates, name="portfolio")
        result = model.estimate_exposure(returns, model_type="FF3")

        assert isinstance(result, FactorExposure)
        assert result.observations == n
        assert result.r_squared > 0.5
        assert abs(result.betas["Mkt-RF"] - 1.1) < 0.2
        assert abs(result.betas["SMB"] - 0.3) < 0.2
        assert abs(result.betas["HML"] - (-0.2)) < 0.2

    def test_insufficient_data(self):
        model = FamaFrenchModel()
        dates = pd.date_range("2023-01-01", periods=5, freq="B")
        model._ff3_cache = pd.DataFrame({
            "Mkt-RF": [0.01] * 5,
            "SMB": [0.005] * 5,
            "HML": [0.003] * 5,
            "RF": [0.0002] * 5,
        }, index=dates)

        returns = pd.Series([0.01] * 5, index=dates)
        result = model.estimate_exposure(returns, model_type="FF3")

        assert result.observations <= 5
        assert "Insufficient" in result.interpretation

    def test_empty_factor_columns(self):
        model = FamaFrenchModel()
        dates = pd.date_range("2023-01-01", periods=100, freq="B")
        model._ff3_cache = pd.DataFrame({
            "col0": [0.01] * 100,
            "RF": [0.0002] * 100,
        }, index=dates)

        returns = pd.Series([0.01] * 100, index=dates)
        result = model.estimate_exposure(returns, model_type="FF3")

        assert "unavailable" in result.interpretation.lower() or result.observations == 0

    def test_factor_exposure_schema_fields(self):
        fe = FactorExposure(
            ticker_or_portfolio="TEST",
            model_type="FF3",
            alpha=0.001,
            alpha_pvalue=0.05,
            betas={"Mkt-RF": 1.0, "SMB": 0.5, "HML": -0.3},
            beta_pvalues={"Mkt-RF": 0.01, "SMB": 0.05, "HML": 0.10},
            r_squared=0.75,
            adj_r_squared=0.74,
            observations=252,
            interpretation="Mkt-RF: β=1.000***; SMB: β=0.500**; HML: β=-0.300*",
        )
        assert fe.betas["Mkt-RF"] == 1.0
        assert fe.model_type == "FF3"
        d = fe.model_dump(mode="json")
        assert "betas" in d
        assert "alpha" in d
