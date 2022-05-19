import json
import socket

def create_connection_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def get_email_from_json():
    email = ""
    with open("server_variables.json") as file:
        data = json.load(file)
        email = data["user"]

    file.close()

    return email


def message_to_headers(message):
    separator = "\r\n"
    header_list = message.split(separator)
    return header_list

def json_from_headers(message):
    '''
    Function that constructs a json object with the header values of the request
    '''
    header_list = message_to_headers(message)
    #we delete the startline
    header_list.pop(0)
    dic = dict()
    for header in header_list[1:]:
        attr_value = header.split(":")
        dic[attr_value[0]]= attr_value[1]
    return json.dumps(dic)

def default_response(head_list:list):
    resp_start_line = "HTTP/1.1 200 OK"
    head_list.insert(0, resp_start_line)

    #we add the custom header 
    email = get_email_from_json()
    head_list.append("X-ElQuePregunta: " + email)

    s = "\r\n".join(head_list) + "\r\n\r\n"
    html = welcome_html()
    return s + html   

def welcome_html():
    return '''
    <html>
        <head>
            <title>Welcome</title>
        </head>
        <body>
            <h1> Welcome </h1>
        <style>
            h1{
                text-align:center;
            }
        </style>
        </body>
    </html>
    ''' 

def blocked_html():
    return '''
    <html>
        <head>
            <title>Forbidden</title>
        </head>
        <body>
            <h1> You shall not pass </h1>
            <p> Restricted access.
        <style>
            h1{
                text-align:center;
                color:red;
            }
            p{
                text-align:center;
            }
        </style>
        </body>
    </html>
    ''' 


def receive_full_message(connection_socket, buff_size, end_of_message):
    '''
    Esta función se encarga de recibir el mensaje completo desde el cliente.
    En caso de que el mensaje sea más grande que el tamaño del buffer 'buff_size',
    esta función va a esperar a que llegue el resto.
    '''

    #recibimos la primera parte del mensaje
    buffer = connection_socket.recv(buff_size)
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
            buffer = connection_socket.recv(buff_size)
            full_message += buffer.decode()

            is_end_of_message = contains_end_of_message(full_message, end_of_message)

            if is_end_of_message:
                #removemos la secuencia de fin de mensaje
                full_message = full_message[0:(len(full_message) - len(end_of_message))]
    
    return full_message


def contains_end_of_message(message, end_sequence):
    return end_sequence == message[(len(message) - len(end_sequence)):len(message)]
