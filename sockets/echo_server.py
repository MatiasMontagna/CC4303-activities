# -*- coding: utf-8 -*-
import socket

#algunas constantes
BUFF_SIZE = 64
END_OF_MSG = "\r\n\r\n"
ADDRESS = ('localhost', 5000)

#auxiliary functions
#-------------------------
def receive_full_message(socket, buff_size, end_of_message):
    '''
    Esta función se encarga de recibir el mensaje completo desde el cliente.
    En caso de que el mensaje sea más grande que el tamaño del buffer 'buff_size',
    esta función va a esperar a que llegue el resto.
    '''

    #recibimos la primera parte del mensaje
    buffer, address = socket.recvfrom(buff_size)
    full_message = buffer.decode()

    #verficiamos si llegó el mensaje completo o si aún faltan partes del mensaje
    is_end_of_message = contains_end_of_message(full_message, end_of_message)

    #si el mensaje llegó completo (o sea que contiene la secuencia de fin de mensaje)
    #removemos la secuencia de fin de mensaje

    if is_end_of_message:
        full_message = full_message[0:(len(full_message) - len(end_of_message))]
    
    #si el mensaje no está completo (no contiene la secuencia de fin de mensaje)
    else:
        #entramos a un while para recibir el resto y seguimos esperando información
        while not is_end_of_message:
            #recibimos un nuevo trozo del mensaje y lo añadimos al mensaje "completo"
            print(full_message)
            other_buffer, _ = socket.recvfrom(buff_size)
            full_message += other_buffer.decode()

            is_end_of_message = contains_end_of_message(full_message, end_of_message)

            if is_end_of_message:
                #removemos la secuencia de fin de mensaje
                full_message = full_message[0:(len(full_message) - len(end_of_message))]
    
    return full_message, address


def contains_end_of_message(message, end_sequence):
    if end_sequence == message[(len(message) - len(end_sequence)):len(message)]:
        return True
    else:
        return False










def is_msg_complete(message: str, end_sequence: str)->bool:
    '''
    Boolean function that returns True if the message contains the ending sequence
    '''
    if message == "": return False
    return end_sequence == message[(len(message) - len(end_sequence)):len(message)]

def proccess_incoming_messages(server_socket, buff_size, end_of_message):
    addres = None
    msg = ""
    while not is_msg_complete(msg, end_of_message):
        msg_bytes, addr = server_socket.recvfrom(buff_size)
        msg += msg_bytes.decode()
        if is_msg_complete(msg, end_of_message):
            break

    return msg[0:(len(msg)-len(end_of_message))], addr
        

print('Creating socket - Echo Server')

#creamos socket y le asignamos dirección
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_socket.bind(ADDRESS)

while True:
    #msg, addr = proccess_incoming_messages(server_socket, BUFF_SIZE, END_OF_MSG)
    #msg, addr = server_socket.recvfrom(BUFF_SIZE)
    msg, addr = receive_full_message(server_socket, BUFF_SIZE, END_OF_MSG)

    print(msg)
    print(addr)

    server_socket.sendto(msg.encode(), addr)

server_socket.close()