import socket
from header import Header
import sys

class RoutingTable():
    pass

class Router:
    def __init__(self, address, routing_table_path):
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.socket.bind(address)
        self.routing_table_path = routing_table_path
        self.address = address if address[0] != 'localhost' else ('127.0.0.1', address[1])  

    def get_final_destination(self, header_message: Header) -> tuple:
        return (header_message.ip_address, header_message.port)

    def handle_message(self):
        data,_ = self.socket.recvfrom(1024)
        header = Header().parse(data.decode())
        final_destination = self.get_final_destination(header)

        if final_destination == self.address :
            print(header.message)
        else:
            self.forward(header)


    def forward(self, header:Header):
        next_hop_address = self.routing_table_lookup(header)
        final_destination = self.get_final_destination(header)
        if next_hop_address == None:
            print("No routes to {0} for {1}".format(final_destination, header))
        else:
            self.socket.sendto(header.encode(), next_hop_address)
            print("Redirecting package '{0}' with final destination '{1}' from '{2}' to '{3}'".format(header, final_destination, self.address, next_hop_address))

    def routing_table_lookup(self, header: Header):
        '''Searches throughout the routing table to find if there exists a router to forward the message'''
        with open(self.routing_table_path, 'r') as routing_table:
            lines = routing_table.readlines()
            for table_entry in lines:
                ip_address_range, init_range_port, end_range_port, dest_ip, dest_port = table_entry.split(' ')

                if self.is_valid_cidr(ip_address_range, int(init_range_port), int(end_range_port), header):
                    return (dest_ip, int(dest_port))

            routing_table.close()

        return None

    def is_valid_cidr(self, ip_address_range, init_range_port, end_range_port, header:Header):
        '''Checks if the destination of the message is inside the cidr range'''
        
        base_ip, byte_mask = ip_address_range.split('/') 

        fixed_byte_numbers = int(byte_mask) // 8

        #check for ip
        for fixed in range(fixed_byte_numbers):
            if header.ip_address.split('.')[fixed] != base_ip.split('.')[fixed]:
                return False

        #check for port
        for port in range(init_range_port, end_range_port + 1):
            if port == header.port:
                return True

        return False


def main():
    args = sys.argv
    ip_address = args[1]
    port = int(args[2])
    routing_table_filename = args[3]

    router = Router((ip_address, port), routing_table_filename)

    while True:
        print("Waiting")
        router.handle_message()

if __name__ == "__main__":
    main()