#!/usr/bin/python
import sys
import socket

KISS_FEND = 0xC0  # Frame start/end marker
KISS_FESC = 0xDB  # Escape character
KISS_TFEND = 0xDC  # If after an escape, means there was an 0xC0 in the source message
KISS_TFESC = 0xDD  # If after an escape, means there was an 0xDB in the source message

if len(sys.argv) < 4:
    print("Usage: %s <source callsign> <destination callsign> <message> [path1 [path2]]" % sys.argv[0])
    sys.exit(1)

# Addresses must be 6 bytes plus the SSID byte, each character shifted left by 1
# If it's the final address in the header, set the low bit to 1
# Ignoring command/response for a simple example
def encode_address(s, final):
    if "-" not in s:
        s = s + "-0"  # default to SSID 0
    call, ssid = s.split('-')
    if len(call) < 6:
        call = call + " " * (6 - len(call))  # pad with spaces
    encoded_call = [ord(x) << 1 for x in call[0:6]]
    encoded_ssid = (int(ssid) << 1) | 0b01100000 | (0b00000001 if final else 0)
    return encoded_call + [encoded_ssid]

# Encode source and destination addresses
src_addr_final = len(sys.argv) == 4
src_addr = encode_address(sys.argv[1].upper(), src_addr_final)
print("src_addr:", " ".join([f"{byte:02X}" for byte in src_addr]))

dest_addr = encode_address(sys.argv[2].upper(), False)
print("dest_addr:", " ".join([f"{byte:02X}" for byte in dest_addr]))

# Initialize path and path2
path = []
path2 = []

# Encode path addresses if present
if len(sys.argv) >= 5:
    path_final = not (len(sys.argv) == 6)
    path = encode_address(sys.argv[3].upper(), path_final)
    print("path:", " ".join([f"{byte:02X}" for byte in path]))

if len(sys.argv) == 6:
    path2 = encode_address(sys.argv[4].upper(), True)
    print("path2:", " ".join([f"{byte:02X}" for byte in path2]))

# Create the elements of a UI frame
c_byte = [0x03]
pid = [0xF0]
msg = [ord(c) for c in sys.argv[-1]]

print("c_byte:", " ".join([f"{byte:02X}" for byte in c_byte]))
print("pid:", " ".join([f"{byte:02X}" for byte in pid]))
print("msg:", " ".join([f"{byte:02X}" for byte in msg]))

# Assemble the packet by concatenating all elements together
packet = dest_addr + src_addr + path + path2 + c_byte + pid + msg

# Escape the packet
packet_escaped = []
for x in packet:
    if x == KISS_FEND:
        packet_escaped += [KISS_FESC, KISS_TFEND]
    elif x == KISS_FESC:
        packet_escaped += [KISS_FESC, KISS_TFESC]
    else:
        packet_escaped += [x]

# Build the frame that we will send to Dire Wolf and turn it into a bytes object
kiss_cmd = 0x00  # Two nybbles combined - TNC 0, command 0 (send data)
kiss_frame = [KISS_FEND, kiss_cmd] + packet_escaped + [KISS_FEND]
output = bytes(kiss_frame)

# Print the hexadecimal representation of the packet
hex_packet = output.hex()
print("Hexadecimal representation of the packet:")
formatted_hex_packet = " ".join([hex_packet[i:i+2] for i in range(0, len(hex_packet), 2)])
print(formatted_hex_packet)

# Connect to Dire Wolf listening on port 8001 on this machine and send the frame
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 8001))
s.send(output)
s.close()
