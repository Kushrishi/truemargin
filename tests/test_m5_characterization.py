from __future__ import annotations

import numpy as np
import pytest

from truemargin.m5_characterization import _assert_close, _score_metrics, build_failure_table


def test_score_metrics_uses_frozen_case_quartile_blind_spot_rule() -> None:
    error = np.arange(1.0, 9.0)
    score = np.arange(8.0, 0.0, -1.0)

    metrics = _score_metrics(error, score)

    expected = (error >= np.percentile(error, 75)) & (score <= np.percentile(score, 25))
    assert np.array_equal(metrics["blind_spot"], expected)
    assert metrics["blind_spot_rate"] == pytest.approx(float(np.mean(expected)))
    assert metrics["spearman"] == pytest.approx(-1.0)


def test_build_failure_table_preserves_all_failure_classes() -> None:
    clean = {
        "sigma_blind_spot_count": 0,
        "sigma_case_spearman": 0.5,
        "sigma_quartile_error_delta_mm": 1.0,
        "invalid_comparators": "",
    }
    blind = clean | {"sigma_blind_spot_count": 1}
    inverted = clean | {"sigma_case_spearman": -0.1}
    nonpositive_enrichment = clean | {"sigma_quartile_error_delta_mm": 0.0}
    invalid = clean | {"invalid_comparators": "ice,residual"}

    failures = build_failure_table([clean, blind, inverted, nonpositive_enrichment, invalid])

    assert failures == [blind, inverted, nonpositive_enrichment, invalid]


def test_assert_close_rejects_reconstruction_drift() -> None:
    _assert_close("same", 0.25, 0.25)
    with pytest.raises(ValueError, match="reconstruction mismatch"):
        _assert_close("drift", 0.25, 0.3)
