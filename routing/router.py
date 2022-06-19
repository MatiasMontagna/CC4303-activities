import socket
from header import Header

class RoutingTable():
    pass

class Router:
    def __init__(self, address):
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.socket.connect(address)

        self.table = RoutingTable()

    def handle_message(self, message):
        header = Header().parse(message)
        if (header.ip_address, header.port) == self.address :
            print(header.message)
        else:
            self.forward(header)

    def forward(self, header:Header):
        pass

    