"""Constants for the Norsup Pool Heat Pump integration."""

DOMAIN = "norsup"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Modbus slave adressen
SLAVE_CMD = 99   # AquaTemp WiFi module (0x63) - voor schrijven
SLAVE_MAIN = 0   # Hoofdcontroller - FC16 sensordata
SLAVE_WIFI = 1   # WiFi module positie - FC03 power/modus/setpoint

# Schrijfadressen (slave 99)
ADDR_POWER          = 1011  # 0=UIT, 1=AAN
ADDR_MODE           = 1012  # 0=koelen, 1=verwarmen, 2=automatisch
ADDR_SETPOINT_HEAT  = 1137  # verwarmingssetpoint (°C x10)
ADDR_SETPOINT_COOL  = 1013  # koelsetpoint (°C x10)
ADDR_SILENCE        = 1076  # silence mode: 0=UIT, 1=AAN

# Setpoint limieten
SETPOINT_HEAT_MIN = 15.0
SETPOINT_HEAT_MAX = 35.0
SETPOINT_COOL_MIN = 15.0
SETPOINT_COOL_MAX = 30.0

# Modi
MODE_COOL = 0
MODE_HEAT = 1
MODE_AUTO = 2

MODE_HA_TO_NORSUP = {
    "cool": MODE_COOL,
    "heat": MODE_HEAT,
    "heat_cool": MODE_AUTO,
}
MODE_NORSUP_TO_HA = {
    MODE_COOL: "cool",
    MODE_HEAT: "heat",
    MODE_AUTO: "heat_cool",
}

# Compressor max frequentie
COMPRESSOR_MAX_HZ = 70  # bevestigd: 70Hz = 100%

# Sensorregisters (FC16 slave 0, startadres 2001)
# Index = offset in het FC16 packet
SENSOR_REGISTERS = {
    "O06": {"index": 19, "name": "Expansion Valve",          "unit": "",    "scale": 1,  "device_class": None},
    "O07": {"index": 20, "name": "Compressor Frequency",     "unit": "Hz",  "scale": 1,  "device_class": None},
    "O08": {"index": 21, "name": "Compressor Current",       "unit": "A",   "scale": 10, "device_class": "current"},
    "O09": {"index": 22, "name": "IPM Temperature",          "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T01": {"index": 44, "name": "Suction Temperature",      "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T02": {"index": 45, "name": "Inlet Water Temperature",  "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T03": {"index": 46, "name": "Outlet Water Temperature", "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T04": {"index": 47, "name": "Coil Temperature",         "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T05": {"index": 48, "name": "Ambient Temperature",      "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T06": {"index": 49, "name": "Exhaust Temperature",      "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T10": {"index": 53, "name": "Pressure Sensor",          "unit": "bar", "scale": 10, "device_class": "pressure"},
    "T11": {"index": 59, "name": "Superheat",                "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T12": {"index": 60, "name": "Fan Speed",                "unit": "rpm", "scale": 1,  "device_class": None},
    "T13": {"index": 61, "name": "Overheat After Comp.",     "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T14": {"index": 62, "name": "Supply Voltage",           "unit": "V",   "scale": 1,  "device_class": "voltage"},
    "T15": {"index": 64, "name": "Antifreeze Temperature",   "unit": "°C",  "scale": 10, "device_class": "temperature"},
    "T16": {"index": 65, "name": "EC Fan Motor Speed",       "unit": "rpm", "scale": 1,  "device_class": None},
    "T17": {"index": 66, "name": "Fan Motor 1 Speed",        "unit": "rpm", "scale": 1,  "device_class": None},
    "T18": {"index": 67, "name": "Fan Motor 2 Speed",        "unit": "rpm", "scale": 1,  "device_class": None},
    "T19": {"index": 68, "name": "Bus Voltage",              "unit": "V",   "scale": 1,  "device_class": "voltage"},
}
