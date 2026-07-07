"""Small shared analytics helpers reused by the services' prediction engines.

Pure Python, with an optional scikit-learn acceleration path (identical result).
Keeping the trend maths here avoids each module re-deriving least squares.
"""

from __future__ import annotations

from typing import Sequence

try:  # pragma: no cover
    import numpy as _np
    from sklearn.linear_model import LinearRegression as _LR

    _HAS_SKLEARN = True
except Exception:  # noqa: BLE001
    _HAS_SKLEARN = False


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def linear_trend(points: Sequence[tuple[float, float]]) -> float:
    """Least-squares slope (units per x) through (x, y) points; 0.0 if undefined."""
    if len(points) < 2:
        return 0.0
    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    if len(set(xs)) < 2:
        return 0.0

    if _HAS_SKLEARN:  # pragma: no cover
        model = _LR().fit(_np.array(xs).reshape(-1, 1), _np.array(ys))
        return float(model.coef_[0])

    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else 0.0


def project(current: float, slope_per_unit: float, horizon: float) -> float:
    """Linear projection of a value ``horizon`` units ahead."""
    return current + slope_per_unit * horizon
