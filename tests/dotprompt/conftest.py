"""Configuration for dotprompt tests.

These tests are marked as optional and will be skipped by default unless
explicitly requested with `pytest -m dotprompt` or `pytest --dotprompt`.
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip dotprompt tests by default unless explicitly requested."""
    # Check if dotprompt tests are explicitly requested
    # Get the marker expression - this can be None, empty string, or the expression
    marker_expr = config.getoption("-m", default=None)
    if marker_expr is None:
        marker_expr = ""
    else:
        marker_expr = str(marker_expr)

    dotprompt_flag = config.getoption("--dotprompt", default=False)
    env_flag = os.environ.get("RUN_DOTPROMPT_TESTS", "").lower() in ("1", "true", "yes")

    # Check if dotprompt marker is requested in the expression
    # Simple check: if marker_expr contains "dotprompt" and doesn't exclude it
    marker_expr_lower = marker_expr.lower().strip()
    has_dotprompt_marker = (
        marker_expr_lower
        and "dotprompt" in marker_expr_lower
        and "not dotprompt" not in marker_expr_lower
    )

    # If not explicitly requested, skip dotprompt tests
    if not (dotprompt_flag or env_flag or has_dotprompt_marker):
        skip_dotprompt = pytest.mark.skip(
            reason="dotprompt tests skipped by default (use -m dotprompt or --dotprompt to run)"
        )
        for item in items:
            if "dotprompt" in [mark.name for mark in item.iter_markers()]:
                item.add_marker(skip_dotprompt)


def pytest_addoption(parser):
    """Add command line option to run dotprompt tests."""
    parser.addoption(
        "--dotprompt",
        action="store_true",
        default=False,
        help="Run dotprompt template engine tests",
    )
