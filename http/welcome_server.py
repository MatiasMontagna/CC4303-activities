import socket
from utils import contains_end_of_message, welcome_html, get_email_from_json, message_to_headers

class WelcomeServer:
    '''
    Simple server that given an HTTP request returns a welcome page
    '''
    def __init__(self, address:(str, int), buffer_size, end_of_message):
        print("Starting Server")
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addres = address
        self.buff_size = buffer_size
        self.end_of_message = end_of_message
        self.msg = None
        self.connection = None

        self.socket.bind(address)
        self.socket.listen(3)

        print('... Waiting requests')

    def receive_full_message(self, connection_socket):

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

    def default_response(self, head_list:list):
        resp_start_line = "HTTP/1.1 200 OK"
        head_list.insert(0, resp_start_line)
        #we add the custom header 
        email = get_email_from_json()
        head_list.append("X-ElQuePregunta: " + email)

        s = "\r\n".join(head_list) + "\r\n\r\n"
        html = welcome_html()
        return s + html   


  
    def wait_for_request(self):
        connection, address = self.socket.accept()
        self.msg = self.receive_full_message(connection)
        self.connection = connection

    def handle_request(self):
        if self.msg == None:
            return
        print(self.msg)
        req_headers = message_to_headers(self.msg)
        response = self.default_response(req_headers)
        
        #We send the response
        self.connection.send(response.encode())

        #We close the connection and reset the 'connection' and 'msg' variables for a new request
        self.connection.close()
        self.connection = None
        self.msg = None
        


    

    
