import socket
from header import IPHeader


client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = IPHeader().build(("127.0.0.1",8883), 10,"Hello world")

client.sendto(msg.encode(), ("127.0.0.1",8881))