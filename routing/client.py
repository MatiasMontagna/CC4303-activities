import socket
from header import Header


client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = Header().build(("127.0.0.1",8885), "Hello world")

client.sendto(msg.encode(), ("127.0.0.1",8881))