# -*- coding: utf-8 -*-
import socket
import sys
from math import ceil


#auxliary functions


print('Creating socket - Client')

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ADDRESS = ('localhost', 5000)


print("... Sending message")


#message = sys.argv[1]
end_of_message = "\r\n\r\n"
buffsize = 1024


# socket debe recibir bytes, por lo que encodeamos el mensaje
send_message = (data + end_of_message).encode()


# enviamos el mensaje a través del socket
client_socket.sendto(send_message, ADDRESS)
print("... Message sent")


# y esperamos una respuesta
message, addr = client_socket.recvfrom(buffsize)
print(' -> Server response: <<' + message.decode() + '>>')

# cerramos la conexión
client_socket.close()
