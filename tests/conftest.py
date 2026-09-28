"""
conftest.py — session-scoped fixtures for DataGuard tests.

Runs each pipeline once per test session and exposes the check results
to all tests via fixtures.
"""

import pytest
from analytics import pipeline_buggy, pipeline_fixed
from checks.guards import run_all_checks, summarize


@pytest.fixture(scope="session")
def buggy_results():
    """Check results produced by the buggy pipeline."""
    result = pipeline_buggy.run()
    return run_all_checks(result)


@pytest.fixture(scope="session")
def fixed_results():
    """Check results produced by the fixed pipeline."""
    result = pipeline_fixed.run()
    return run_all_checks(result)


@pytest.fixture(scope="session")
def buggy_summary(buggy_results):
    return summarize(buggy_results)


@pytest.fixture(scope="session")
def fixed_summary(fixed_results):
    return summarize(fixed_results)
