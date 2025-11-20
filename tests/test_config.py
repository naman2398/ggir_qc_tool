"""
Tests for configuration module
"""

import pytest
from config.settings import config


def test_supported_devices():
    """Test that supported devices list is not empty."""
    assert len(config.SUPPORTED_DEVICES) > 0


def test_device_phase_mapping():
    """Test that phase mapping contains correct devices."""
    assert config.DEVICE_ACTICAL in config.DEVICE_PHASE_MAPPING
    assert config.DEVICE_PHILIPS in config.DEVICE_PHASE_MAPPING


def test_target_files():
    """Test that all required target files are defined."""
    assert 'csv' in config.TARGET_FILES
    assert 'pdf_sleep' in config.TARGET_FILES
    assert 'pdf_data' in config.TARGET_FILES


def test_path_templates():
    """Test that path templates contain required placeholders."""
    assert '{device}' in config.PATH_TEMPLATE_STANDARD
    assert '{pid}' in config.PATH_TEMPLATE_STANDARD
    assert '{phase}' in config.PATH_TEMPLATE_PHASED
