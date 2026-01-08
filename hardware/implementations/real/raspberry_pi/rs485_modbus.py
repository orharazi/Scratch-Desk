#!/usr/bin/env python3
"""
RS485 Modbus RTU Interface for Sensor Reading
==============================================

This module handles communication with sensors connected via RS485 using Modbus RTU protocol.
Each sensor is a separate Modbus slave device on the RS485 bus.

Hardware Connection:
- RS485 adapter connected to Raspberry Pi UART (e.g., /dev/ttyAMA0)
- Up to 247 Modbus slave devices can be connected on the bus
- Each sensor has a unique slave address (configurable in settings.json)

Protocol:
- Modbus RTU (binary protocol over RS485)
- Function Code 02 (Read Discrete Inputs) for digital sensor reading
- Default: 9600 baud, 8N1 (8 data bits, no parity, 1 stop bit)

The RS485 interface allows reading 12 piston position sensors through serial communication,
replacing the multiplexer approach.
"""

import time
import threading
from typing import Optional, Dict
from core.logger import get_logger

# Try to import pymodbus library
try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    ModbusSerialClient = None
    ModbusException = Exception


class RS485ModbusInterface:
    """Interface for reading sensors via RS485 Modbus RTU protocol"""

    def __init__(
        self,
        port: str = '/dev/ttyAMA0',
        baudrate: int = 9600,
        bytesize: int = 8,
        parity: str = 'N',
        stopbits: int = 1,
        timeout: float = 1.0,
        sensor_addresses: Optional[Dict[str, int]] = None
    ):
        """
        Initialize RS485 Modbus RTU interface

        Args:
            port: Serial port device path (e.g., /dev/ttyAMA0, /dev/ttyUSB0)
            baudrate: Communication speed (default: 9600)
            bytesize: Data bits (default: 8)
            parity: Parity bit - 'N'=None, 'E'=Even, 'O'=Odd (default: N)
            stopbits: Stop bits (default: 1)
            timeout: Read timeout in seconds (default: 1.0)
            sensor_addresses: Dictionary mapping sensor names to Modbus slave addresses
        """
        self.logger = get_logger()
        self.port = port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.sensor_addresses = sensor_addresses or {}

        # Modbus client
        self.client: Optional[ModbusSerialClient] = None
        self.is_connected = False

        # Thread lock for serial communication
        self.lock = threading.Lock()

        # Check if pymodbus is available
        if not MODBUS_AVAILABLE:
            self.logger.error("pymodbus library not available! Install with: pip3 install pymodbus", category="hardware")
            self.logger.error("RS485 communication will not work without pymodbus", category="hardware")
            raise ImportError("pymodbus library required for RS485 communication")

        self.logger.info(
            f"RS485 Modbus RTU interface initialized: port={port}, baudrate={baudrate}, format={bytesize}{parity}{stopbits}",
            category="hardware"
        )
        self.logger.debug(f"Configured sensors: {len(self.sensor_addresses)}", category="hardware")

    def connect(self) -> bool:
        """
        Connect to RS485 Modbus RTU bus

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected:
            self.logger.debug("RS485 already connected", category="hardware")
            return True

        try:
            self.logger.info(f"Connecting to RS485 on {self.port}...", category="hardware")

            # Create Modbus RTU client
            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                method='rtu'  # Modbus RTU protocol
            )

            # Connect to the bus
            if self.client.connect():
                self.is_connected = True
                self.logger.success(f"RS485 connected on {self.port}", category="hardware")
                return True
            else:
                self.logger.error(f"Failed to connect to RS485 on {self.port}", category="hardware")
                return False

        except Exception as e:
            self.logger.error(f"RS485 connection error: {e}", category="hardware")
            return False

    def disconnect(self):
        """Disconnect from RS485 bus"""
        if self.client and self.is_connected:
            self.logger.info("Disconnecting RS485...", category="hardware")
            self.client.close()
            self.is_connected = False
            self.logger.success("RS485 disconnected", category="hardware")

    def read_sensor(self, sensor_name: str, register_address: int = 0) -> Optional[bool]:
        """
        Read digital sensor value via Modbus RTU

        Args:
            sensor_name: Name of sensor (used for logging and address lookup)
            register_address: Modbus register/coil address to read (default: 0)

        Returns:
            True if sensor is triggered (HIGH), False if not triggered (LOW), None on error
        """
        if not self.is_connected:
            self.logger.error("RS485 not connected - cannot read sensor", category="hardware")
            return None

        # Get slave address for this sensor
        slave_address = self.sensor_addresses.get(sensor_name)
        if slave_address is None:
            self.logger.error(f"No RS485 address configured for sensor: {sensor_name}", category="hardware")
            return None

        try:
            with self.lock:
                # Read Discrete Input (function code 02) - for digital sensors
                # Read 1 bit from the specified register address
                response = self.client.read_discrete_inputs(
                    address=register_address,
                    count=1,
                    slave=slave_address
                )

                # Check if read was successful
                if response.isError():
                    self.logger.error(
                        f"Modbus read error for {sensor_name} (slave {slave_address}): {response}",
                        category="hardware"
                    )
                    return None

                # Extract boolean value from response
                sensor_state = bool(response.bits[0])
                return sensor_state

        except ModbusException as e:
            self.logger.error(f"Modbus exception reading {sensor_name}: {e}", category="hardware")
            return None
        except Exception as e:
            self.logger.error(f"Error reading sensor {sensor_name}: {e}", category="hardware")
            return None

    def read_sensor_with_retry(
        self,
        sensor_name: str,
        register_address: int = 0,
        retries: int = 2
    ) -> Optional[bool]:
        """
        Read sensor with automatic retry on failure

        Args:
            sensor_name: Name of sensor
            register_address: Modbus register address
            retries: Number of retry attempts on failure

        Returns:
            Sensor state or None on error
        """
        for attempt in range(retries + 1):
            result = self.read_sensor(sensor_name, register_address)
            if result is not None:
                return result

            if attempt < retries:
                self.logger.warning(
                    f"Retry {attempt + 1}/{retries} for sensor {sensor_name}",
                    category="hardware"
                )
                time.sleep(0.01)  # 10ms delay before retry

        return None

    def read_multiple_sensors(self, sensor_names: list) -> Dict[str, Optional[bool]]:
        """
        Read multiple sensors efficiently

        Args:
            sensor_names: List of sensor names to read

        Returns:
            Dictionary mapping sensor names to their states
        """
        results = {}
        for sensor_name in sensor_names:
            results[sensor_name] = self.read_sensor(sensor_name)
        return results

    def test_connection(self) -> bool:
        """
        Test RS485 connection by attempting to read from first configured sensor

        Returns:
            True if test successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Cannot test - RS485 not connected", category="hardware")
            return False

        if not self.sensor_addresses:
            self.logger.warning("No sensors configured - cannot test connection", category="hardware")
            return False

        # Try reading first sensor
        first_sensor = list(self.sensor_addresses.keys())[0]
        self.logger.info(f"Testing RS485 connection with sensor: {first_sensor}", category="hardware")

        result = self.read_sensor(first_sensor)
        if result is not None:
            self.logger.success(f"RS485 test successful - read {first_sensor} = {result}", category="hardware")
            return True
        else:
            self.logger.error("RS485 test failed - could not read sensor", category="hardware")
            return False

    def get_sensor_address(self, sensor_name: str) -> Optional[int]:
        """Get Modbus slave address for a sensor"""
        return self.sensor_addresses.get(sensor_name)

    def set_sensor_address(self, sensor_name: str, address: int):
        """Set Modbus slave address for a sensor"""
        if 1 <= address <= 247:
            self.sensor_addresses[sensor_name] = address
            self.logger.debug(f"Set {sensor_name} address to {address}", category="hardware")
        else:
            self.logger.error(f"Invalid Modbus address {address} (must be 1-247)", category="hardware")

    def cleanup(self):
        """Cleanup and disconnect"""
        self.disconnect()


if __name__ == "__main__":
    """Test RS485 interface"""
    from core.logger import get_logger

    logger = get_logger()

    logger.info("="*60, category="hardware")
    logger.info("RS485 Modbus RTU Interface Test", category="hardware")
    logger.info("="*60, category="hardware")

    # Example sensor addresses (configure these in settings.json)
    test_sensors = {
        "line_marker_up_sensor": 1,
        "line_marker_down_sensor": 2,
        "line_cutter_up_sensor": 3,
    }

    # Create RS485 interface
    rs485 = RS485ModbusInterface(
        port='/dev/ttyAMA0',
        baudrate=9600,
        sensor_addresses=test_sensors
    )

    # Connect
    if rs485.connect():
        logger.info("Connected successfully!", category="hardware")

        # Test connection
        rs485.test_connection()

        # Read sensors
        logger.info("Reading sensors...", category="hardware")
        for sensor_name in test_sensors.keys():
            state = rs485.read_sensor(sensor_name)
            state_str = "TRIGGERED" if state else "READY" if state is not None else "ERROR"
            logger.info(f"  {sensor_name}: {state_str}", category="hardware")

        # Cleanup
        rs485.cleanup()
    else:
        logger.error("Connection failed", category="hardware")

    logger.info("="*60, category="hardware")
    logger.info("Test complete", category="hardware")
    logger.info("="*60, category="hardware")
