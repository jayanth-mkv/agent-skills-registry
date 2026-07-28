#!/usr/bin/env python3
"""Compare two binomial email outcomes or plan a fixed-horizon two-arm experiment."""

from __future__ import annotations

import argparse
import json
import math
import sys
from statistics import NormalDist
from typing import Any


class ExperimentError(ValueError):
    """Raised when experiment inputs cannot support the requested calculation."""


def validate_probability(value: float, label: str, *, open_interval: bool = False) -> float:
    valid = 0 < value < 1 if open_interval else 0 <= value <= 1
    if not valid:
        interval = "between 0 and 1, exclusive" if open_interval else "from 0 through 1"
        raise ExperimentError(f"{label} must be {interval}")
    return value


def validate_counts(successes: int, total: int, label: str) -> None:
    if total <= 0:
        raise ExperimentError(f"{label} total must be positive")
    if successes < 0 or successes > total:
        raise ExperimentError(f"{label} successes must be between 0 and total")


def z_for_confidence(confidence: float) -> float:
    validate_probability(confidence, "confidence", open_interval=True)
    return NormalDist().inv_cdf(0.5 + confidence / 2)


def wilson_interval(successes: int, total: int, confidence: float) -> tuple[float, float]:
    validate_counts(successes, total, "interval")
    z = z_for_confidence(confidence)
    rate = successes / total
    z2 = z * z
    denominator = 1 + z2 / total
    center = (rate + z2 / (2 * total)) / denominator
    half_width = (
        z
        * math.sqrt(rate * (1 - rate) / total + z2 / (4 * total * total))
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def compare_proportions(
    control_successes: int,
    control_total: int,
    variant_successes: int,
    variant_total: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    validate_counts(control_successes, control_total, "control")
    validate_counts(variant_successes, variant_total, "variant")
    z_critical = z_for_confidence(confidence)

    control_rate = control_successes / control_total
    variant_rate = variant_successes / variant_total
    difference = variant_rate - control_rate
    unpooled_se = math.sqrt(
        control_rate * (1 - control_rate) / control_total
        + variant_rate * (1 - variant_rate) / variant_total
    )
    difference_interval = (
        difference - z_critical * unpooled_se,
        difference + z_critical * unpooled_se,
    )

    pooled_rate = (control_successes + variant_successes) / (
        control_total + variant_total
    )
    pooled_se = math.sqrt(
        pooled_rate
        * (1 - pooled_rate)
        * (1 / control_total + 1 / variant_total)
    )
    if pooled_se:
        z_statistic = difference / pooled_se
        p_value = 2 * (1 - NormalDist().cdf(abs(z_statistic)))
    else:
        z_statistic = 0.0
        p_value = 1.0

    control_interval = wilson_interval(control_successes, control_total, confidence)
    variant_interval = wilson_interval(variant_successes, variant_total, confidence)
    if difference_interval[0] > 0:
        direction = "variant_higher"
    elif difference_interval[1] < 0:
        direction = "variant_lower"
    else:
        direction = "inconclusive_at_selected_confidence"

    return {
        "schema_version": "1.0",
        "analysis_type": "two_arm_binomial_comparison",
        "confidence": confidence,
        "control": {
            "successes": control_successes,
            "total": control_total,
            "rate": control_rate,
            "wilson_interval": list(control_interval),
        },
        "variant": {
            "successes": variant_successes,
            "total": variant_total,
            "rate": variant_rate,
            "wilson_interval": list(variant_interval),
        },
        "effect": {
            "absolute_difference": difference,
            "relative_lift": (
                difference / control_rate if control_rate else None
            ),
            "normal_approximation_interval": list(difference_interval),
            "two_sided_z_statistic": z_statistic,
            "two_sided_p_value": p_value,
            "direction": direction,
        },
        "interpretation_limits": [
            "The calculation assumes independent Bernoulli outcomes and a pre-specified two-arm comparison.",
            "It does not repair biased assignment, repeated peeking, sample-ratio mismatch, bot activity, attrition, or attribution error.",
            "Statistical separation is not the same as practical value; compare the effect with a pre-declared minimum worthwhile effect and guardrails.",
            "Use a clustering-aware or sequential method when the randomization or stopping design requires one.",
        ],
    }


def plan_two_arm_experiment(
    baseline_rate: float,
    minimum_detectable_effect: float,
    confidence: float = 0.95,
    power: float = 0.80,
) -> dict[str, Any]:
    validate_probability(baseline_rate, "baseline rate")
    validate_probability(confidence, "confidence", open_interval=True)
    validate_probability(power, "power", open_interval=True)
    if minimum_detectable_effect == 0:
        raise ExperimentError("minimum detectable effect must be non-zero")
    variant_rate = baseline_rate + minimum_detectable_effect
    validate_probability(variant_rate, "baseline rate plus minimum detectable effect")

    alpha = 1 - confidence
    z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
    z_power = NormalDist().inv_cdf(power)
    pooled_midpoint = (baseline_rate + variant_rate) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled_midpoint * (1 - pooled_midpoint))
        + z_power
        * math.sqrt(
            baseline_rate * (1 - baseline_rate)
            + variant_rate * (1 - variant_rate)
        )
    ) ** 2
    per_arm = math.ceil(numerator / (minimum_detectable_effect**2))

    return {
        "schema_version": "1.0",
        "analysis_type": "fixed_horizon_two_arm_plan",
        "assumptions": {
            "baseline_rate": baseline_rate,
            "variant_rate_at_mde": variant_rate,
            "minimum_detectable_absolute_effect": minimum_detectable_effect,
            "confidence": confidence,
            "power": power,
            "allocation": "1:1",
            "test": "two-sided independent proportions",
        },
        "sample_size": {
            "per_arm": per_arm,
            "total": per_arm * 2,
        },
        "planning_limits": [
            "This is a normal-approximation fixed-horizon plan for one primary binomial metric.",
            "Increase the target for expected attrition, exclusions, clustering, multiple comparisons, delayed outcomes, or unequal allocation.",
            "Do not stop early from repeated significance checks unless a valid sequential design was chosen in advance.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare = subparsers.add_parser("compare", help="Compare control and variant success counts.")
    compare.add_argument("--control-successes", type=int, required=True)
    compare.add_argument("--control-total", type=int, required=True)
    compare.add_argument("--variant-successes", type=int, required=True)
    compare.add_argument("--variant-total", type=int, required=True)
    compare.add_argument("--confidence", type=float, default=0.95)
    compare.add_argument("--format", choices=("text", "json"), default="text")

    plan = subparsers.add_parser("plan", help="Plan a balanced fixed-horizon experiment.")
    plan.add_argument("--baseline-rate", type=float, required=True)
    plan.add_argument(
        "--minimum-detectable-effect",
        type=float,
        required=True,
        help="Absolute rate-point change expressed as a decimal, such as 0.002 for 0.2 percentage points.",
    )
    plan.add_argument("--confidence", type=float, default=0.95)
    plan.add_argument("--power", type=float, default=0.80)
    plan.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.3f}%"


def render_text(report: dict[str, Any]) -> str:
    if report["analysis_type"] == "two_arm_binomial_comparison":
        control = report["control"]
        variant = report["variant"]
        effect = report["effect"]
        lines = [
            "Email experiment comparison",
            (
                f"Control: {control['successes']}/{control['total']} "
                f"({percent(control['rate'])})"
            ),
            (
                f"Variant: {variant['successes']}/{variant['total']} "
                f"({percent(variant['rate'])})"
            ),
            (
                f"Effect: {percent(effect['absolute_difference'])} absolute; "
                f"{percent(effect['relative_lift'])} relative"
            ),
            (
                f"Two-sided p-value: {effect['two_sided_p_value']:.6g}; "
                f"decision signal: {effect['direction']}"
            ),
            "Limits:",
        ]
        lines.extend(f"- {item}" for item in report["interpretation_limits"])
        return "\n".join(lines)

    assumptions = report["assumptions"]
    sample = report["sample_size"]
    lines = [
        "Email experiment plan",
        (
            f"Baseline: {percent(assumptions['baseline_rate'])}; "
            f"MDE: {percent(assumptions['minimum_detectable_absolute_effect'])}"
        ),
        (
            f"Target: {sample['per_arm']} recipients per arm "
            f"({sample['total']} total)"
        ),
        "Limits:",
    ]
    lines.extend(f"- {item}" for item in report["planning_limits"])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        if args.command == "compare":
            report = compare_proportions(
                args.control_successes,
                args.control_total,
                args.variant_successes,
                args.variant_total,
                args.confidence,
            )
        else:
            report = plan_two_arm_experiment(
                args.baseline_rate,
                args.minimum_detectable_effect,
                args.confidence,
                args.power,
            )
    except ExperimentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
