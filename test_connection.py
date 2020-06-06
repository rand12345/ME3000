import socket
import struct
import time

# Create a TCP/IP socket
TCP_IP = '192.168.1.198'
TCP_PORT = 8899
BUFFER_SIZE = 77
sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
sock.connect ((TCP_IP, TCP_PORT))

try:
    req = struct.pack ('8B', 0x01, 0x03, 0x00, 0x00, 0x00, 0x24, 0x45, 0xD1)
    sock.send (req)
    print ("TX: (%s)" % req)
    rec = sock.recv (BUFFER_SIZE)
    print ("RX: (%s)" % rec)
    for i in rec:
        print(hex (ord (i)))
        x = int (hex (ord (i)), 16)
        print(x)
    time.sleep (10)


finally:
    print ('\nCLOSING SOCKET')
    sock.close ()
