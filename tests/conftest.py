"""Pytest configuration and fixtures for test suite."""


import pytest
from core.services.test_manager import test_manager


@pytest.fixture(autouse=True)
def reset_test_manager():
    """Reset test_manager state at the start and end of each test."""
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()
    yield
    if test_manager.is_running:
        test_manager.stop_test()
    if test_manager.is_stopped:
        test_manager.finalize_test()



