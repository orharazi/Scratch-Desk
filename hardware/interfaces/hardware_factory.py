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
from core.logger import get_logger

# Module-level logger
logger = get_logger()


def load_config(config_path: str = "config/settings.json") -> Dict:
    """Load configuration from settings.json"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load config from {config_path}: {e}", category="hardware")
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

    logger.info("="*60, category="hardware")
    logger.info("Hardware Factory - Creating Hardware Interface", category="hardware")
    logger.info("="*60, category="hardware")
    logger.info(f"Configuration: {config_path}", category="hardware")
    logger.info(f"Mode: {'REAL HARDWARE' if use_real_hardware else 'MOCK/SIMULATION'}", category="hardware")
    logger.info("="*60, category="hardware")

    if use_real_hardware:
        # Import and return real hardware interface
        from hardware.implementations.real.real_hardware import RealHardware
        return RealHardware(config_path)
    else:
        # Import and return mock hardware interface
        from hardware.implementations.mock.mock_hardware import MockHardware
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


def switch_hardware_mode(use_real: bool, config_path: str = "config/settings.json"):
    """
    Switch hardware mode at runtime (hot-swap).

    This function handles the complete hardware switch process:
    1. Shutdown existing hardware instance cleanly
    2. Create new hardware instance (Mock or Real)
    3. Update the global singleton reference

    Args:
        use_real: True for real hardware, False for mock/simulation
        config_path: Path to settings.json configuration file

    Returns:
        Tuple of (new_hardware_instance, success: bool, error_message: str)
    """
    global _hardware_instance

    logger.info("=" * 60, category="hardware")
    logger.info("HARDWARE HOT-SWAP - Switching Hardware Mode", category="hardware")
    logger.info("=" * 60, category="hardware")
    logger.info(f"Target mode: {'REAL HARDWARE' if use_real else 'MOCK/SIMULATION'}", category="hardware")

    # Step 1: Shutdown existing hardware if any
    if _hardware_instance is not None:
        logger.info("Shutting down existing hardware instance...", category="hardware")
        try:
            if hasattr(_hardware_instance, 'shutdown'):
                _hardware_instance.shutdown()
                logger.info("Hardware shutdown completed", category="hardware")
            elif hasattr(_hardware_instance, 'cleanup'):
                _hardware_instance.cleanup()
                logger.info("Hardware cleanup completed", category="hardware")
        except Exception as e:
            logger.warning(f"Warning during hardware shutdown: {e}", category="hardware")
        _hardware_instance = None

    # Step 2: Create new hardware instance
    try:
        if use_real:
            logger.info("Creating Real Hardware instance...", category="hardware")
            from hardware.implementations.real.real_hardware import RealHardware
            _hardware_instance = RealHardware(config_path)

            # Check if initialization was successful
            if hasattr(_hardware_instance, 'is_initialized') and not _hardware_instance.is_initialized:
                error_msg = getattr(_hardware_instance, 'initialization_error', 'Unknown initialization error')
                logger.error(f"Real hardware initialization failed: {error_msg}", category="hardware")
                return _hardware_instance, False, error_msg

            logger.info("Real Hardware instance created successfully", category="hardware")
        else:
            logger.info("Creating Mock Hardware instance...", category="hardware")
            from hardware.implementations.mock.mock_hardware import MockHardware
            _hardware_instance = MockHardware(config_path)
            logger.info("Mock Hardware instance created successfully", category="hardware")

        logger.info("=" * 60, category="hardware")
        logger.info("HARDWARE HOT-SWAP COMPLETE", category="hardware")
        logger.info("=" * 60, category="hardware")

        return _hardware_instance, True, ""

    except Exception as e:
        error_msg = f"Failed to create hardware instance: {str(e)}"
        logger.error(error_msg, category="hardware")
        logger.info("=" * 60, category="hardware")
        return None, False, error_msg


if __name__ == "__main__":
    """Test hardware factory"""
    logger.info("="*60, category="hardware")
    logger.info("Hardware Factory Test", category="hardware")
    logger.info("="*60, category="hardware")

    # Create hardware interface
    hardware = create_hardware_interface()

    logger.info(f"Created hardware interface: {type(hardware).__name__}", category="hardware")
    logger.info(f"Module: {type(hardware).__module__}", category="hardware")

    # Test basic functionality
    if hasattr(hardware, 'initialize'):
        logger.debug("Hardware has initialize() method", category="hardware")
    if hasattr(hardware, 'move_x'):
        logger.debug("Hardware has move_x() method", category="hardware")
    if hasattr(hardware, 'get_current_x'):
        logger.debug("Hardware has get_current_x() method", category="hardware")

    logger.info("="*60, category="hardware")
    logger.info("Factory test completed", category="hardware")
    logger.info("="*60, category="hardware")
