#!/usr/bin/env python3
"""Tests for analyze_email_experiment.py."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from analyze_email_experiment import (
    ExperimentError,
    compare_proportions,
    plan_two_arm_experiment,
    wilson_interval,
)


class AnalyzeEmailExperimentTests(unittest.TestCase):
    def test_compare_reports_effect_and_uncertainty(self) -> None:
        report = compare_proportions(100, 10_000, 140, 10_000)
        self.assertAlmostEqual(report["control"]["rate"], 0.01)
        self.assertAlmostEqual(report["variant"]["rate"], 0.014)
        self.assertAlmostEqual(report["effect"]["absolute_difference"], 0.004)
        self.assertEqual(report["effect"]["direction"], "variant_higher")
        self.assertLess(report["effect"]["two_sided_p_value"], 0.05)

    def test_compare_can_be_inconclusive(self) -> None:
        report = compare_proportions(100, 1_000, 105, 1_000)
        self.assertEqual(
            report["effect"]["direction"],
            "inconclusive_at_selected_confidence",
        )

    def test_wilson_interval_is_bounded_for_zero_successes(self) -> None:
        lower, upper = wilson_interval(0, 50, 0.95)
        self.assertEqual(lower, 0.0)
        self.assertGreater(upper, 0)
        self.assertLess(upper, 0.1)

    def test_plan_returns_balanced_positive_sample(self) -> None:
        report = plan_two_arm_experiment(0.02, 0.004)
        self.assertGreater(report["sample_size"]["per_arm"], 0)
        self.assertEqual(
            report["sample_size"]["total"],
            report["sample_size"]["per_arm"] * 2,
        )

    def test_invalid_counts_are_rejected(self) -> None:
        with self.assertRaises(ExperimentError):
            compare_proportions(11, 10, 1, 10)

    def test_cli_json_output(self) -> None:
        script = Path(__file__).with_name("analyze_email_experiment.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "compare",
                "--control-successes",
                "10",
                "--control-total",
                "1000",
                "--variant-successes",
                "15",
                "--variant-total",
                "1000",
                "--format",
                "json",
            ],
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        report = json.loads(completed.stdout)
        self.assertEqual(report["analysis_type"], "two_arm_binomial_comparison")


if __name__ == "__main__":
    unittest.main()
