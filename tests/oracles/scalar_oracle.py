"""Direct equation and analytical root-count oracle for Cong's scalar laboratory."""

from __future__ import annotations

from math import isfinite, tanh

from scipy.optimize import brentq


def _parameters(inner_feedback: float, learning_gain: float) -> tuple[float, float]:
    feedback = float(inner_feedback)
    gain = float(learning_gain)
    if not isfinite(feedback) or abs(feedback) >= 1.0:
        raise ValueError("inner_feedback must be finite with absolute value below one")
    if not isfinite(gain) or gain <= 0.0:
        raise ValueError("learning_gain must be finite and positive")
    return feedback, gain


def direct_paper_update(
    theta: float,
    *,
    inner_feedback: float,
    learning_gain: float,
    intervention: float = 0.0,
) -> float:
    """Evaluate the scalar paper equation directly, without package code."""

    feedback, gain = _parameters(inner_feedback, learning_gain)
    if not isfinite(theta) or not isfinite(intervention):
        raise ValueError("theta and intervention must be finite")
    behavior = (theta + intervention) / (1.0 - feedback)
    return gain * tanh(behavior)


def analytical_root_count(composite_gain: float) -> int:
    """Count zero-intervention roots using oddness and strict concavity on the positive axis.

    For ``x = tanh(g x)``, ``tanh(g x) - x`` is strictly concave for ``x > 0``.
    Its derivative at zero is ``g - 1`` and its value at one is negative. Thus there
    is one root when ``g <= 1`` and exactly three roots when ``g > 1``.
    """

    gain = float(composite_gain)
    if not isfinite(gain) or gain <= 0.0:
        raise ValueError("composite_gain must be finite and positive")
    return 1 if gain <= 1.0 else 3


def scalar_bracketed_roots(
    *,
    inner_feedback: float,
    learning_gain: float,
    tolerance: float,
) -> tuple[float, ...]:
    """Bracket the roots after the analytical root count determines their number."""

    feedback, gain = _parameters(inner_feedback, learning_gain)
    if not isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    composite_gain = gain / (1.0 - feedback)
    if analytical_root_count(composite_gain) == 1:
        return (0.0,)

    def residual(theta: float) -> float:
        return direct_paper_update(
            theta,
            inner_feedback=feedback,
            learning_gain=gain,
        ) - theta

    lower = gain * 1e-7
    upper = gain
    if residual(lower) <= 0.0 or residual(upper) >= 0.0:
        raise RuntimeError("analytical positive-root bracket was not observed numerically")
    positive = float(brentq(residual, lower, upper, xtol=tolerance, rtol=1e-15))
    return (-positive, 0.0, positive)
