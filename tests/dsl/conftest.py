"""
Minimal conftest for DSL tool tests.

These tests don't need the full unified store fixtures.
"""

import pytest


@pytest.fixture
def mock_reter():
    """Return None - DSL tests use mocked reter."""
    return None
