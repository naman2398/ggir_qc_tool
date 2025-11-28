"""Tests for configuration module"""

import pytest
from config import settings


def test_supported_devices():
    assert len(settings.SUPPORTED_DEVICES) > 0


def test_device_phase_mapping():
    assert settings.DEVICE_ACTICAL in settings.DEVICE_PHASE_MAPPING
    assert settings.DEVICE_PHILIPS in settings.DEVICE_PHASE_MAPPING


def test_target_files():
    assert "csv" in settings.TARGET_FILES
    assert "pdf_sleep" in settings.TARGET_FILES
    assert "pdf_data" in settings.TARGET_FILES


def test_path_templates():
    assert "{device}" in settings.PATH_TEMPLATE_STANDARD
    assert "{pid}" in settings.PATH_TEMPLATE_STANDARD
    assert "{phase}" in settings.PATH_TEMPLATE_PHASED
