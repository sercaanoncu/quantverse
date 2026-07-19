import numpy as np
import pandas as pd
import pytest

import project.optimization.black_litterman as black_litterman
from project.optimization.black_litterman import (
    black_litterman_posterior,
    black_litterman_weights,
)


def test_black_litterman_posterior_falls_back_to_prior_without_views():
    assets = ["AAA", "BBB", "CCC"]
    covariance = pd.DataFrame(np.eye(3) * 0.04, index=assets, columns=assets)
    caps = pd.Series([300.0, 200.0, 100.0], index=assets)
    posterior = black_litterman_posterior(covariance, caps)

    assert posterior["prior_returns"].shape == (3,)
    assert posterior["posterior_returns"].equals(
        posterior["prior_returns"].rename("Posterior_Return")
    )


def test_black_litterman_weights_sum_to_one_and_reject_missing_caps():
    assets = ["AAA", "BBB", "CCC", "DDD"]
    covariance = pd.DataFrame(np.eye(4) * 0.04, index=assets, columns=assets)
    caps = pd.Series([400.0, 300.0, 200.0, 100.0], index=assets)
    weights = black_litterman_weights(covariance, caps, max_weight=0.40)

    assert weights.sum() == pytest.approx(1.0)
    assert weights.max() <= 0.40 + 1e-8
    with pytest.raises(ValueError, match="positive market caps"):
        black_litterman_weights(
            covariance, caps.mask(caps.index == "DDD"), max_weight=0.40
        )


def test_black_litterman_optimizer_failure_is_not_silently_relabelled(
    monkeypatch,
):
    class FailedResult:
        success = False
        message = "synthetic optimizer failure"

    monkeypatch.setattr(
        black_litterman,
        "minimize",
        lambda *args, **kwargs: FailedResult(),
    )
    assets = ["AAA", "BBB", "CCC", "DDD"]
    covariance = pd.DataFrame(np.eye(4) * 0.04, index=assets, columns=assets)
    caps = pd.Series([400.0, 300.0, 200.0, 100.0], index=assets)

    with pytest.raises(ValueError, match="synthetic optimizer failure"):
        black_litterman_weights(covariance, caps, max_weight=0.40)
