"""Tests for auth helper utilities"""

from src.auth.user_auth import extract_username_from_email


def test_extract_username_from_email_replaces_dots_with_underscore():
    username = extract_username_from_email("john.doe@stonybrook.edu")
    assert username == "john_doe"


def test_extract_username_from_email_strips_and_normalizes():
    username = extract_username_from_email("  John+DOE@stonybrook.edu  ")
    assert username == "john_doe"


def test_extract_username_from_email_invalid_returns_fallback():
    username = extract_username_from_email("not-an-email")
    assert username == "unknown_user"
