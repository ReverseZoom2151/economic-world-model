"""Verify Cong's exact scalar DDGE laboratory by bracketing and iteration."""

from __future__ import annotations

from ewm.scenarios.scalar import paper_config, scalar_verification_report


def main() -> None:
    config = paper_config()
    report = scalar_verification_report(config)

    assert len(report.bracketing_roots) == 3
    assert report.stable == (True, False, True)
    assert max(report.fixed_point_residuals) < 1e-10
    for root, derivative, stable in zip(
        report.bracketing_roots,
        report.derivatives,
        report.stable,
        strict=True,
    ):
        print(f"theta={root: .8f}  derivative={derivative: .8f}  stable={stable}")


if __name__ == "__main__":
    main()
