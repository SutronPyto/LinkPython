OTT Hydromet Sat/XLink readme for JSON Telemetry Formatting
===========================================================

Overview
--------
This script is designed to format telemetry data from a weather station or similar device into JSON format for transmission. It is particularly useful for users who need to send structured data to an MQTT broker or other data collection systems.

Features
--------
- **Data Formatting**: Converts CSV data into a structured JSON format.
- **ISO8601 Date and Time**: Formats date and time into ISO8601 standard.
- **Customizable**: Allows configuration of station name, time offset, and missing data indicators.
- **Location Data**: Includes station location (latitude, longitude, elevation) in the JSON output.

Setup Instructions
------------------
1. **Station Name**: Set the station name of the XLink to the device ID configured in your MQTT broker.
2. **TX(n) Fields Configuration**: Configure the following fields via LinkComm:
    - Enable: [x]
    - Radio type: [Cell]
    - Kind: [Scheduled]
    - Custom script format: [x]
    - Script format function: [JSON_TxFormat]
3. **Measurements Configuration**: Ensure measurements are configured and enabled for transmission via Telemetry(n).
4. **General Purpose Variables**: Define the following variables via LinkComm to transmit the station's location:
    - GP1: Latitude (e.g., 38.996983)
    - GP2: Longitude (e.g., -77.424065)
    - GP3: Elevation (e.g., 88.000000)

Usage
-----
- **Telemetry Data**: The script processes telemetry data in CSV format and converts it into JSON.
- **Testing**: If the script is tested, it uses fixed sample data for demonstration purposes.
- **Customization**: Adjust the `CSV_LIMIT` variable to change the number of CSV lines processed.

Why Use This Script?
--------------------
- **Standardized Data**: Ensures your telemetry data is in a consistent and structured JSON format.
- **Ease of Integration**: Simplifies the process of sending data to MQTT brokers or other systems.
- **Flexibility**: Easily configurable to match your specific data transmission needs.
- **Location Inclusion**: Automatically includes station location data in the JSON output.

This script is ideal for users who need a reliable and customizable way to format and transmit telemetry data from their devices.

For further assistance, please refer to the comments within the script or contact support.

