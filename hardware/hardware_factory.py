#!/usr/bin/env python3

"""
Hardware Factory
================

Factory pattern to create appropriate hardware interface based on configuration.
Automatically selects between mock hardware (simulation) and real hardware
(Raspberry Pi + Arduino) based on settings.json.
"""

import json
from typing import Dict, Optional


def load_config(config_path: str = "config/settings.json") -> Dict:
    """Load configuration from settings.json"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        return {}


def create_hardware_interface(config_path: str = "config/settings.json"):
    """
    Factory method to create appropriate hardware interface.

    Args:
        config_path: Path to settings.json configuration file

    Returns:
        Hardware interface instance (either MockHardware or RealHardware)
    """
    config = load_config(config_path)
    use_real_hardware = config.get("hardware_config", {}).get("use_real_hardware", False)

    print(f"\n{'='*60}")
    print("Hardware Factory - Creating Hardware Interface")
    print(f"{'='*60}")
    print(f"Configuration: {config_path}")
    print(f"Mode: {'REAL HARDWARE' if use_real_hardware else 'MOCK/SIMULATION'}")
    print(f"{'='*60}\n")

    if use_real_hardware:
        # Import and return real hardware interface
        from hardware.real_hardware import RealHardware
        return RealHardware(config_path)
    else:
        # Import and return mock hardware interface
        from hardware.mock_hardware import MockHardware
        return MockHardware(config_path)


# Convenience singleton for global access
_hardware_instance: Optional[object] = None


def get_hardware_interface(config_path: str = "config/settings.json"):
    """
    Get or create singleton hardware interface instance.

    Args:
        config_path: Path to settings.json configuration file

    Returns:
        Hardware interface instance (singleton)
    """
    global _hardware_instance

    if _hardware_instance is None:
        _hardware_instance = create_hardware_interface(config_path)

    return _hardware_instance


def reset_hardware_interface():
    """Reset the singleton instance (useful for testing)"""
    global _hardware_instance
    _hardware_instance = None


if __name__ == "__main__":
    """Test hardware factory"""
    print("\n" + "="*60)
    print("Hardware Factory Test")
    print("="*60 + "\n")

    # Create hardware interface
    hardware = create_hardware_interface()

    print(f"\nCreated hardware interface: {type(hardware).__name__}")
    print(f"Module: {type(hardware).__module__}")

    # Test basic functionality
    if hasattr(hardware, 'initialize'):
        print("\n✓ Hardware has initialize() method")
    if hasattr(hardware, 'move_x'):
        print("✓ Hardware has move_x() method")
    if hasattr(hardware, 'get_current_x'):
        print("✓ Hardware has get_current_x() method")

    print("\n" + "="*60)
    print("Factory test completed")
    print("="*60 + "\n")
