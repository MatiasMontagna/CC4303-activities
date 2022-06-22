from header import IPHeader
import socket
import sys

incomplete_header = sys.argv[1]
initial_ip = sys.argv[2]
initial_port = int(sys.argv[3])

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


with open('prueba_router.txt') as f:
    lines = f.readlines()
    for line_message in lines:
        header = IPHeader().parse(incomplete_header + ',' + line_message)
        udp_socket.sendto(header.encode(), (initial_ip, initial_port))