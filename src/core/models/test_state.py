"""Test state enumeration for tracking test session status."""
from enum import Enum


class TestState(Enum):
    """Enumeration of all possible test states."""
    NOTHING = "nothing"
    PREPARED = "prepared"
    RUNNING = "running"
    STOPPED = "stopped"  # Test stopped (recording ended) but not yet finalized
