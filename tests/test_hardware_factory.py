#!/usr/bin/env python3

import pytest
from hardware.interfaces.hardware_factory import (
    create_hardware_interface,
    get_hardware_interface,
    reset_hardware_interface,
    switch_hardware_mode
)
from hardware.implementations.mock.mock_hardware import MockHardware


class TestCreateHardware:
    """Test hardware interface creation"""

    def test_create_mock_hardware(self, settings_file):
        """Should create MockHardware when use_real_hardware is False"""
        hardware = create_hardware_interface(settings_file)
        assert isinstance(hardware, MockHardware)

    def test_create_returns_initialized(self, settings_file):
        """Created hardware should have expected attributes"""
        hardware = create_hardware_interface(settings_file)
        assert hasattr(hardware, 'move_x')
        assert hasattr(hardware, 'move_y')
        assert hasattr(hardware, 'initialize')
        assert hasattr(hardware, 'shutdown')


class TestSingletonPattern:
    """Test hardware factory singleton behavior"""

    def test_singleton_pattern(self, settings_file):
        """get_hardware_interface should return same instance"""
        hw1 = get_hardware_interface(settings_file)
        hw2 = get_hardware_interface(settings_file)
        assert hw1 is hw2

    def test_reset_clears_singleton(self, settings_file):
        """reset_hardware_interface should allow new instance"""
        hw1 = get_hardware_interface(settings_file)
        reset_hardware_interface()
        hw2 = get_hardware_interface(settings_file)
        # After reset, new instance created
        assert hw1 is not hw2


class TestSwitchMode:
    """Test hardware mode switching"""

    def test_switch_to_mock(self, settings_file):
        """Should switch to mock hardware successfully"""
        hw, success, error_msg = switch_hardware_mode(use_real=False, config_path=settings_file)
        assert success is True
        assert error_msg == ""
        assert isinstance(hw, MockHardware)

    def test_switch_shuts_down_previous(self, settings_file):
        """Switching should shutdown previous hardware"""
        # Create initial instance
        hw1 = get_hardware_interface(settings_file)
        hw1.initialize()
        assert hw1.is_initialized is True

        # Switch mode (shuts down previous)
        hw2, success, error_msg = switch_hardware_mode(use_real=False, config_path=settings_file)
        assert success is True

        # Old instance should be shut down
        assert hw1.is_initialized is False


class TestMultipleSwitches:
    """Test multiple mode switches"""

    def test_multiple_switches(self, settings_file):
        """Should handle multiple switches without issues"""
        # Switch to mock
        hw1, success1, _ = switch_hardware_mode(use_real=False, config_path=settings_file)
        assert success1 is True
        assert isinstance(hw1, MockHardware)

        # Switch again to mock
        hw2, success2, _ = switch_hardware_mode(use_real=False, config_path=settings_file)
        assert success2 is True
        assert isinstance(hw2, MockHardware)

        # Instances should be different (new instance created)
        assert hw1 is not hw2
