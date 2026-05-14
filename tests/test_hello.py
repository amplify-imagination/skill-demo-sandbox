import pytest

from app.hello import greet


def test_greet_basic():
    assert greet("world") == "Hello, world!"


def test_greet_named():
    assert greet("Stig") == "Hello, Stig!"


def test_greet_empty_raises():
    with pytest.raises(ValueError):
        greet("")
