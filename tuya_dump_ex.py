import sys
import serial
import binascii
import struct

# Define the packet marker
PACKET_MARKER = b'\x55\xaa'  #


def calculate_checksum(data):
    """
    Calculates the Tuya protocol checksum.
    The checksum is the sum of all bytes from the header, divided by 256 to get the remainder.
    """
    checksum = sum(data) % 256  #
    return checksum


def parse_data_units(data):
    """
    Parses the data section of a Tuya packet based on the "Data Units" format.
    Returns a list of parsed data points (DPs).
    """
    parsed_dps = []
    offset = 0
    while offset < len(data):
        # Each data unit has a fixed format: DP ID (1 byte) + DP Type (1 byte) + DP Length (2 bytes) + DP Value (N bytes)
        if offset + 4 > len(data):
            parsed_dps.append({"error": "Incomplete data unit", "raw_data": data[offset:]})
            break

        try:
            dp_id, dp_type, dp_length = struct.unpack('>BBH', data[offset:offset + 4]) # > (big-endian), B (unsigned char), B (unsigned char), H (unsigned short)
        except struct.error:
            parsed_dps.append({"error": "Failed to unpack data unit header", "raw_data": data[offset:]})
            break

        offset += 4

        # Extract the DP value based on DP length
        if offset + dp_length > len(data):
            parsed_dps.append({
                "error": f"Incomplete data unit value (expected {dp_length} bytes)", #
                "dp_id": dp_id,
                "dp_type": dp_type,
                "dp_length": dp_length,
                "raw_data": data[offset - 4:] # Include the data unit header
            })
            break

        dp_value = data[offset:offset + dp_length]
        offset += dp_length

        # Decode the DP value based on DP type
        decoded_value = dp_value
        if dp_type == 0:  # Raw type
            # No further decoding needed, keep as bytes
            pass
        elif dp_type == 1:  # Boolean type
            decoded_value = bool(dp_value == b'\x01')  # Convert to boolean
        elif dp_type == 2:  # Value type (4-byte integer)
            if dp_length == 4:
                decoded_value = struct.unpack('>i', dp_value)[0]  # Get the integer value
            else:
                decoded_value = {"error": f"Invalid length for value type ({dp_length} bytes)", "raw_value": dp_value}
        elif dp_type == 3:  # String type
            decoded_value = dp_value.decode('utf-8', errors='ignore')  # Decode as UTF-8, ignore errors
        elif dp_type == 4:  # Enum type (1 byte)
            if dp_length == 1:
                decoded_value = int.from_bytes(dp_value, 'big')  # Convert byte to integer
            else:
                decoded_value = {"error": f"Invalid length for enum type ({dp_length} bytes)", "raw_value": dp_value}
        elif dp_type == 5:  # Bitmap type (4-byte integer)
            if dp_length == 4:
                decoded_value = struct.unpack('>I', dp_value)[0]  # Get the unsigned integer value
            else:
                decoded_value = {"error": f"Invalid length for bitmap type ({dp_length} bytes)", "raw_value": dp_value}
        else:
            decoded_value = {"error": f"Unknown DP type ({dp_type})", "raw_value": dp_value}

        parsed_dps.append({
            "dp_id": dp_id,
            "dp_type": dp_type,
            "dp_length": dp_length,
            "dp_value": decoded_value,
            "raw_value": dp_value
        })

    return parsed_dps


def parse_tuya_packet(packet_data):
    """
    Parses a packet assuming the Tuya serial port protocol format,
    including decoding the data units.
    Returns a dictionary with parsed fields if the packet is valid.
    """
    # Tuya packet format: Header (2) + Version (1) + Command (1) + Data length (2) + Data (N) + Checksum (1)
    if len(packet_data) < 7:
        return {"error": "Packet too short", "raw_data": packet_data}

    try:
        version, command, data_length = struct.unpack('>BHB', packet_data[2:6])
    except struct.error:
        return {"error": "Failed to unpack header fields", "raw_data": packet_data}

    expected_packet_size = 6 + data_length + 1
    if len(packet_data) < expected_packet_size:
        return {"error": f"Packet too short for declared data length ({data_length} bytes)", "raw_data": packet_data}

    data = packet_data[6:6 + data_length]
    received_checksum = packet_data[6 + data_length]

    calculated_checksum = calculate_checksum(packet_data[:6 + data_length])

    if calculated_checksum != received_checksum:
        return {
            "error": "Checksum mismatch",
            "calculated": calculated_checksum,
            "received": received_checksum,
            "raw_data": packet_data
        }

    # Packet is valid, parse the data units
    parsed_data = parse_data_units(data)

    return {
        "version": version,
        "command": command,
        "data_length": data_length,
        "data": data,
        "checksum": received_checksum,
        "parsed_data_units": parsed_data
    }


def hexdump_packet(packet_data):
    """
    Prints a hexdump of the given packet data.
    """
    offset = 0
    while offset < len(packet_data):
        line = packet_data[offset:offset + 16]
        hex_line = ' '.join(f'{byte:02x}' for byte in line)
        ascii_line = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in line)
        print(f'{offset:08x}: {hex_line.ljust(48)} |{ascii_line}|')
        offset += 16


def read_and_hexdump_packets(tty_device):
    """
    Reads binary data from the specified TTY device, detects packets based on the marker,
    parses Tuya packets and data units, and prints hexdump and parsed data.
    """
    buffer = b''
    packet_count = 0

    try:
        # Open the TTY device
        # tty_device is expected to be a string here
        ser = serial.Serial(tty_device, 9600, timeout=1)  # Example: 9600 baud, 1-second timeout
        ser.close()
        ser.open()

        print(f"Reading from TTY device: {tty_device}")

        while True:
            chunk = ser.read(1024)
            if not chunk:
                continue

            buffer += chunk

            while PACKET_MARKER in buffer:
                marker_index = buffer.find(PACKET_MARKER)

                if marker_index > 0:
                    print("--- Unexpected data before packet marker ---")
                    hexdump_packet(buffer[:marker_index])
                    buffer = buffer[marker_index:]

                buffer = buffer[len(PACKET_MARKER):]

                next_marker_index = buffer.find(PACKET_MARKER)

                if next_marker_index == -1:
                    packet_data = buffer
                    buffer = b''
                else:
                    packet_data = buffer[:next_marker_index]
                    buffer = buffer[next_marker_index:]

                packet_count += 1
                print(f"\n--- Packet {packet_count} (Raw) ---")
                hexdump_packet(PACKET_MARKER + packet_data)

                parsed_packet = parse_tuya_packet(PACKET_MARKER + packet_data)

                if "error" in parsed_packet:
                    print(f"--- Packet {packet_count} Parsing Error: {parsed_packet['error']} ---")
                else:
                    print(f"--- Packet {packet_count} (Parsed Tuya) ---")
                    print(f"  Version: {parsed_packet['version']}")
                    print(f"  Command: {parsed_packet['command']} (0x{parsed_packet['command']:02x})")
                    print(f"  Data Length: {parsed_packet['data_length']} bytes")
                    print(f"  Checksum: {parsed_packet['checksum']} (0x{parsed_packet['checksum']:02x})")

                    if parsed_packet['parsed_data_units']:
                        print("  Data Units:")
                        for dp in parsed_packet['parsed_data_units']:
                            if "error" in dp:
                                print(f"    - Error: {dp['error']}")
                                print(f"      Raw data: {binascii.hexlify(dp.get('raw_data', b'')).decode('ascii')}")
                            else:
                                print(f"    - DP ID: {dp['dp_id']}")
                                print(f"      DP Type: {dp['dp_type']}")
                                print(f"      DP Length: {dp['dp_length']} bytes")
                                print(f"      DP Value: {dp['dp_value']}")
                                print(f"      Raw Value: {binascii.hexlify(dp['raw_value']).decode('ascii')}")


    except serial.SerialException as e:
        print(f"Error opening or reading from serial port {tty_device}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'ser' in locals() and ser.isOpen():
            ser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hexdump_packets_tuya_dataunits.py <tty_device>")
        sys.exit(1)

    tty_device_path = sys.argv[1]  # Get the TTY device path (the first argument after the script name)
    read_and_hexdump_packets(tty_device_path)

