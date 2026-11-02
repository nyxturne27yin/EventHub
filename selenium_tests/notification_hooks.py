"""Pytest report hook used by notification Selenium evidence capture."""
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if call.when == "call":
        item.rep_call = outcome.get_result()
