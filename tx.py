#!/usr/bin/python
import sys
import socket

KISS_FEND = 0xC0  # Frame start/end marker
KISS_FESC = 0xDB  # Escape character
KISS_TFEND = 0xDC  # If after an escape, means there was an 0xC0 in the source message
KISS_TFESC = 0xDD  # If after an escape, means there was an 0xDB in the source message


#Encode KISS Call SSID Destination 
def encode_address(s, final):
    try:
        digi = False

        if "-" not in s:
            s = s + "-0"  # default to SSID 0
        if "*" in s:
            digi = True
            s = s.replace('*', '')

        call, ssid = s.split('-')
        
        if len(call) < 6:
            call = call + " " * (6 - len(call))  # pad with spaces
        
        encoded_call = [ord(x) << 1 for x in call[0:6]]
        encoded_ssid = (int(ssid) << 1) | 0b01100000 | (0b00000001 if final else 0)

        # Include the 7th bit in the SSID byte based on the 'digi' flag
        if digi:
            encoded_ssid |= 0x80

        return encoded_call + [encoded_ssid]
    
    except ValueError as e:
        print("Error encoding address:", e)

# Encode KISS Frame
def encode_ui_frame(source, destination, message, *paths):

    src_addr_final = not paths or (len(paths) == 1 and paths[0] == '')  # src_addr_final is True if no paths are provided
    src_addr = encode_address(source.upper(), src_addr_final)
    dest_addr = encode_address(destination.upper(), False)

    # Ensure paths is a list of strings
    if isinstance(paths, (tuple, list)) and len(paths) == 1 and isinstance(paths[0], str):
        paths = paths[0].split(',')
    elif not all(isinstance(path, str) for path in paths):
        print("Invalid paths format. Returning None.")
        return None

    encoded_paths = [] if not paths or paths[0] == '' else [encode_address(path.upper(), final) for final, path in zip([False] * (len(paths) - 1) + [True], paths)]

    c_byte = [0x03]
    pid = [0xF0]
    msg = [ord(c) for c in message]

    packet = dest_addr + src_addr + sum(encoded_paths, []) + c_byte + pid + msg

    packet_escaped = []
    for x in packet:
        if x == KISS_FEND:
            packet_escaped.append(KISS_FESC)
            packet_escaped.append(KISS_TFEND)
        elif x == KISS_FESC:
            packet_escaped.append(KISS_FESC)
            packet_escaped.append(KISS_TFESC)
        else:
            packet_escaped.append(x)

    kiss_cmd = 0x00
    kiss_frame = [KISS_FEND, kiss_cmd] + packet_escaped + [KISS_FEND]

    kiss_frame = bytes(kiss_frame)
        
    return kiss_frame

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python script.py <source> <destination> <payload> <paths>")
        #if payload contains spaces use quotes to encapsulate it. "payload quoted like this"
        sys.exit(1)

    source = sys.argv[1]
    destination = sys.argv[2]
    message = sys.argv[3]
    paths = sys.argv[4:] if len(sys.argv) > 4 else []  # If paths are not provided, use an empty list

    # Get the KISS frame
    kiss_frame = encode_ui_frame(source, destination, message, *paths)

    # Connect to Dire Wolf listening on port 8001 on this machine and send the frame
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 8001))
    s.send(kiss_frame)
    s.close()
