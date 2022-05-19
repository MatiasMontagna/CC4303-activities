import socket
import json
from utils import receive_full_message,create_connection_socket, contains_end_of_message, welcome_html,blocked_html, get_email_from_json, message_to_headers
from math import ceil

class ProxyServer:
    '''
    Proxy server that given a request fetchs the response and redirects it
    '''
    def __init__(self, address:(str, int), buffer_size, end_of_message):
        print("Starting Server")
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addres = address
        self.buff_size = buffer_size
        self.end_of_message = end_of_message
        self.msg = None
        self.connection = None
        self.user, self.blocked, self.forbidden_words = self.load_server_variables()

        self.socket.bind(address)
        self.socket.listen(3)

        print('... Waiting requests')
        print('Blocked Hosts:')
        for blocked in self.blocked:
            print(blocked)
        print("")

    def receive_full_message(self, connection_socket):
        '''
        Función entregada en las capsulas de EOL
        '''
        #we receive the first part of the message
        buffer = connection_socket.recv(self.buff_size)
        full_message = buffer.decode()

        #we check if the message is complete
        is_end_of_message = contains_end_of_message(full_message, self.end_of_message)

        if is_end_of_message:
            full_message = full_message[0:(len(full_message) - len(self.end_of_message))]
        
        #si el mensaje no está completo (no contiene la secuencia de fin de mensaje)
        else:
            #entramos a un while para recibir el resto y seguimos esperando información
            while not is_end_of_message:
                #recibimos un nuevo trozo del mensaje y lo añadimos al mensaje "completo"
                buffer = connection_socket.recv(self.buff_size)
                full_message += buffer.decode()

                is_end_of_message = contains_end_of_message(full_message, self.end_of_message)

                if is_end_of_message:
                    #removemos la secuencia de fin de mensaje
                    full_message = full_message[0:(len(full_message) - len(self.end_of_message))]
        
        return full_message 
    

    def load_server_variables(self):
        '''
        Carga las variables del json como estados internos del servidor.
        '''
        with open("server_variables.json") as file:
            variables = json.load(file)
            user = variables["user"]
            blocked = variables["blocked"]
            forbidden_words = variables["forbidden_words"]
            return user, blocked, forbidden_words 

  
    def wait_for_request(self, verbose=False):
        '''
        Espera una conexión, y cuando esta llega, la acepta y recibe su mensaje.
        '''
        connection, address = self.socket.accept()
        self.msg = self.receive_full_message(connection)
        self.connection = connection
        if verbose:
            print(self.msg+"\n")
            


    def handle_request(self, verbose=False):
        '''
        Procesa el mensaje, y decide que acción tomar al respecto.
        '''
        host="cc4303.bachmann.cl"
        path="secret"
        message = f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nContent-Type: text/html; charset=UTF-8"
        end_of_message = "\r\n\r\n"

        #we check if the domain is blocked
        domain = get_domain(self.msg)
        if domain in self.blocked:
            header_list = message_to_headers(self.msg)
            resp = blocked_response(header_list)
        
        #domain not blocked
        else:
            socket = create_connection_socket()
            socket.connect((host, 80))

            self.msg = add_custom_header(self.msg)
            
            send_message = (self.msg + end_of_message).encode()
            socket.send(send_message)          
            resp = self.get_full_response(socket)
            socket.close()

        if verbose:
            print(resp+"\n")
        #we send message    
        self.connection.send(resp.encode())

        #we reset server state
        self.connection.close()
        self.connection = None
        self.msg = None


    def get_full_response(self, conn_socket):
        '''
        Parses the HEAD, adds custom header, then with the Content-Length value parses the BODY
        '''
        head, body = parse_head(conn_socket)

        n_bytes = get_content_length(head)

        body += parse_body(conn_socket, n_bytes)

        body = replace_forbidden_words(body, self.forbidden_words)

        return head + body


def parse_head(conn_socket):
    '''
    Parses the HEAD and checks if there is some BODY in it
    '''
    end_of_head = "\r\n\r\n"
    buff_size = 64
    head = ""
    while not is_head_complete(head):
        buffer = conn_socket.recv(buff_size)
        head += buffer.decode()
    
    #if there's some of the BODY in the head variable, we separate them
    head, body = separate_head_from_body(head)

    return head, body

def add_custom_header(head):
    '''
    Adds a custom header to the HEAD
    '''
    email = get_email_from_json()
    head_list = head.split("\r\n")

    head_list.insert(1, "X-ElQuePregunta: " + email)

    return "\r\n".join(head_list)

def get_content_length(head):

    #we skip the startline of the head
    for header in head.split("\r\n")[1:]:
        tag_values = header.split(":")
        if tag_values[0] == "Content-Length":
           return int(tag_values[1])
    return 0

def parse_body(conn_socket, n_bytes):
    '''
    Given the size in bytes of the body, parses it
    '''
    body = ""
    if n_bytes == 0:
        return body

    buffsize = 1024 

    #we calculate the times we will need to fetch the bytes from socket
    n_iterations = ceil(n_bytes / buffsize)

    for i in range(n_iterations):
        body_bytes = conn_socket.recv(buffsize)
        body += body_bytes.decode()
    return body

def is_head_complete(head)->bool:
    '''
    If the head contains the string "\\r\\n\\r\\n" returns True else False
    '''
    return True if "\r\n\r\n" in head else False

def separate_head_from_body(head):
    '''
    Checks if there are parts of the body in the head message, and separates them.
    '''
    end_of_head = "\r\n\r\n"
    
    #finds the end of the HEAD
    index = head.find(end_of_head)
    head_end_index = index + len(end_of_head)

    #separation
    body = head[head_end_index:]
    head = head[:head_end_index]

    return head, body

def blocked_response(header_list):
    '''
    Generates the response that a client receives when trying to access blocked content.
    '''
    s = "HTTP/1.1 403 Forbidden\r\n"
    for header in header_list[1:]:
        s+= header + "\r\n"
    s += "\r\n"

    html = blocked_html()
    return s + html  

def is_blocked(domain):
    return False

def get_domain(message):
    '''
    Gets the startine of the message and then the domain URL
    '''

    startline= message.split("\r\n")[0]

    return startline.split()[1]


def replace_forbidden_words(body, forbidden_words):
    '''
    Given a dictionary of forbidden words. Checks the BODY and replaces the words that are in that dictionary.
    '''
    for dic in forbidden_words:

        for word in dic.keys():
            #word is replaced by dic[word]
            body = dic[word].join(body.split(word))

    return body

    