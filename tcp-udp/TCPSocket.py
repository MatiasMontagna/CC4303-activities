import socket
import sys
import random
from math import ceil
from errors import  DataSizeException, SeqError, FinError, SyncError


class TCPHeader:
    def __init__(self):
        self.syn: int = None
        self.ack: int = None
        self.fin: int = None
        self.seq: int = None
        self.data: str = None

    def __str__(self):
        s = "{0}|||{1}|||{2}|||{3}|||{4}"
        return s.format(self.syn, self.ack, self.fin, self.seq, self.data)
    
    def byte_len(self):
        return len(self.__str__().encode())

    @staticmethod
    def parse(message:str):
        """
        Parses a [SYN]|||[ACK]|||[FIN]|||[SEQ]|||[DATA] string and returns a TCPHeader object."""

        header_list = message.split("|||")
        header = TCPHeader()
        header.syn = int(header_list[0])
        header.ack = int(header_list[1])
        header.fin = int(header_list[2])
        header.seq = int(header_list[3])
        header.data = header_list[4]
        return header
    
    @staticmethod
    def build_string(syn:int, ack:int, fin:int, seq:int, data:str=""):
        '''
        Builds a TCP header string from the parameters given.
        '''
        if len(data.encode()) > 64:
            raise DataSizeException(f"packet data exceeds 64 bytes: {data}")

        return "{0}|||{1}|||{2}|||{3}|||{4}".format(syn, ack, fin, seq, data)


header=TCPHeader().parse(" 0|||0|||0|||98|||Hello world")
assert 0 == header.syn
assert 0 == header.ack
assert 0 == header.fin
assert 98 == header.seq
assert "Hello world" == header.data
assert "0|||0|||0|||98|||Hello world" == TCPHeader().build_string(0, 0, 0, 98, "Hello world")


class TCPSocket:
    '''
    simple TCP socket implementation. Built using UDP socket
    '''   
    
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0
        self.buff_size = 1024
        self.bytes_left = 0
        self.last_message = None
        self.destination_addr = None
        self.origin_addr = None
        self.timeout = None

    def settimeout(self, timeout_seconds):
        '''sets maximum waiting time (in seconds).'''
        self.socket.settimeout(timeout_seconds)
        self.timeout = timeout_seconds

    def bind(self, address):
        self.socket.bind(address)
        self.origin_addr = address

    def connect(self, address):
        '''
        Client side of the three way handshake
        '''
        #random seq is generated
        self.seq = random.randint(0, 100)

        first = False
        second = False
        third = False
        not_sent = True
        #1 => SYN
        syn_msg = TCPHeader().build_string(1, 0, 0, self.seq)
        while not_sent:
            try:
                self.socket.sendto(syn_msg.encode(), address)
                header_bytes, connection_addr = self.socket.recvfrom(self.buff_size)
                not_sent = False

            except TimeoutError: 
                continue
        
        #2 SYN + ACK <==

        header = TCPHeader().parse(header_bytes.decode())

        if header.syn != 1 or header.ack != 1:
            raise SyncError(f"Expected SYN + ACK but got {header.syn} and {header.ack}")
        if self.seq + 1 != header.seq:
            raise SeqError("Received {0}. Expected {1}".format(header.seq, self.seq + 1))
        self.seq = header.seq

        #3 ==> ACK
        ack_msg = TCPHeader().build_string(0, 1, 0, self.seq + 1)
        self.socket.sendto(ack_msg.encode(), connection_addr)
        self.seq += 1
        self.destination_addr = connection_addr
    
    def accept(self):
        '''
        Server side of the three way handshake
        '''
        #1 SYN <==
        not_received = True

        connection = TCPSocket()
        connection.bind((self.origin_addr[0], self.origin_addr[1]+1))
        connection.settimeout(self.timeout)

        while not_received:
            try:
                header_bytes, other_addr = self.socket.recvfrom(self.buff_size)
                header = TCPHeader().parse(header_bytes.decode())
                #if header.fin == 1:

                if header.syn != 1:
                    raise SyncError(f"Expected SYN but got {header.syn}")
                #self.seq = header.seq
                connection.seq = header.seq
                not_received = False
            
            except TimeoutError:
                continue

        #2 ==> SYN + ACK
        not_received = True
        msg = TCPHeader().build_string(1, 1, 0, connection.seq + 1)
        while not_received:
            try:
                connection.socket.sendto(msg.encode(), other_addr)
                connection.last_message = msg

                #3 ACK <==
                data, _ = connection.socket.recvfrom(self.buff_size)
                header = TCPHeader().parse(data.decode())
                if header.seq < connection.seq+2: #mensaje repetido
                    connection.socket.sendto(connection.last_message.encode(), other_addr)
                else:
                    if header.ack != 1:
                        print("header is: ", header)
                        raise SyncError(f"Expected ACK but got {header.ack}")
                    if header.seq != connection.seq+2:
                        raise SeqError("Received {0}. Expected {1}".format(header.seq, connection.seq + 2))

                    not_received = False

            except TimeoutError:
                continue

        connection.seq = header.seq
        connection.destination_addr = other_addr
        return connection, connection.destination_addr

    def send(self, message:bytes):
        
        message_length, n_chunks, message_chunks = divide_message(message.decode(), 64)
        not_send = [True for chunk in message_chunks]   

        #len of data is sent
        len_info = TCPHeader().build_string(0, 0, 0, self.seq, str(message_length))
        ack_not_received = True
        while ack_not_received:
            try:
                bytes_sent = len(len_info.encode())
                self.socket.sendto(len_info.encode(), self.destination_addr)
                data, _ = self.socket.recvfrom(self.buff_size)
                self.last_message = len_info
               
                header = TCPHeader().parse(data.decode())
                if header.seq < self.seq:
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                else:
                    assert header.ack == 1
                    assert self.seq + bytes_sent == header.seq 
                    ack_not_received = False
                    self.seq += bytes_sent

            except TimeoutError:
                continue
        
        current_chunk=0
        #chunks are sent
        while current_chunk < n_chunks:
            try:
                msg = TCPHeader().build_string(0, 0, 0, self.seq, message_chunks[current_chunk])
                bytes_sent= len(msg.encode())
                self.socket.sendto(msg.encode(), self.destination_addr)
                self.last_message = msg
                data, _ = self.socket.recvfrom(self.buff_size)

                header = TCPHeader().parse(data.decode())
                if header.seq <= self.seq:
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                else:
                    assert header.ack == 1
                    if self.seq + bytes_sent != header.seq:
                        sum = self.seq + bytes_sent
                        raise SeqError("Received {0}. Expected {1}+{2}={3}".format(header.seq, self.seq, bytes_sent, sum)) 
                    self.seq += bytes_sent
                    current_chunk += 1

            except TimeoutError:
                #print("current chunk: ",current_chunk)
                #print("last message: ", self.last_message)
                continue
        
        return message_length
    
    def recv(self, buff_size):
        while self.bytes_left == 0: #new recv
            try:
                data, _ = self.socket.recvfrom(buff_size)
                parsed_data = TCPHeader().parse(data.decode())

                if parsed_data.seq < self.seq: #repeated message
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                
                elif parsed_data.fin == 1: #close connection
                    self.recv_close()
                    return

                else: #new message
                    bytes_received = parsed_data.byte_len()
                    message_length = int(parsed_data.data)
                    self.bytes_left = message_length
                    self.seq += bytes_received
                    ack = TCPHeader().build_string(0, 1, 0, self.seq) 
                    self.socket.sendto(ack.encode(), self.destination_addr)
                    self.last_message = ack

            except TimeoutError:
                continue
        
        byte_cap = min(self.bytes_left, buff_size)

        acum_message =""
        while len(acum_message.encode()) < byte_cap:
            try:
                
                data, _ = self.socket.recvfrom(buff_size)
                header = TCPHeader().parse(data.decode())

                if header.seq < self.seq: #repeated message
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                
                elif header.fin == 1:
                    self.recv_close()
                    return

                else: #new message
                    bytes_received = header.byte_len()
                    
                    acum_message+= header.data
                    self.bytes_left-= len(header.data.encode())
                    self.seq += bytes_received
                    ack = TCPHeader().build_string(0, 1, 0, self.seq) 
                    self.socket.sendto(ack.encode(), self.destination_addr)
                    self.last_message = ack

            except TimeoutError:
                #print("current bytes: ",len(acum_message.encode()))
                #print("bytes left: ", self.bytes_left)
                #print("byte cap: ", byte_cap)
                #print("last message: ", self.last_message)
                if self.bytes_left <= 0:
                    break 
                continue
        
        return acum_message.encode()

    def close(self):
        '''
        closes connection with another TCPSocket
        '''

        if self.destination_addr == None:
            self.socket.close()
            return

        fin_header = TCPHeader().build_string(0, 0, 1, self.seq)
        self.last_message = fin_header
        closed = False
        while not closed:
            try:
                self.socket.sendto(fin_header.encode(), self.destination_addr)
                fin_ack_data, _ = self.socket.recvfrom(self.buff_size)
                fin_ack_header = TCPHeader().parse(fin_ack_data.decode())

                if fin_ack_header.seq < self.seq:
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                
                else:    
                    if fin_ack_header.fin != 1 or fin_ack_header.ack!= 1:
                        raise FinError("Expected FIN + ACK, got {0} and {1}".format(fin_ack_header.fin, fin_ack_header.ack))

                    if fin_ack_header.seq != self.seq+1:
                        print(fin_ack_header)
                        raise SeqError("Received {0}. Expected {1}".format(fin_ack_header.seq, self.seq + 1))
                    
                    self.seq += 2
                    ack_header = TCPHeader().build_string(0, 1, 0, self.seq)
                    self.socket.sendto(ack_header.encode(), self.destination_addr)
                    closed = True

            except TimeoutError:
                continue
        
        #reset variables
        self.bytes_left = 0
        self.destination_addr = None
        self.last_message = None
        self.socket.close()

    def recv_close(self):
        '''
        This function is called after a socket receives a FIN message in recv.
        '''

        self.seq += 1
        fin_ack_header = TCPHeader().build_string(0, 1, 1, self.seq)
        finalized = False
        while not finalized:
            try:       
                self.socket.sendto(fin_ack_header.encode(), self.destination_addr)
                self.last_message = fin_ack_header

                ack, _ = self.socket.recvfrom(self.buff_size)
                ack_header = TCPHeader().parse(ack.decode())

                if ack_header.seq < self.seq: #repeated message
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                    continue

                if ack_header.ack!= 1:
                    raise FinError("Expected ACK, got {0}".format(ack_header.ack))

                if ack_header.seq != self.seq+1:
                    raise SeqError("Received {0}. Expected {1}".format(ack_header.seq, self.seq + 1))

                finalized = True
            except TimeoutError:
                continue

        #reset variables
        self.bytes_left = 0
        self.destination_addr = None
        self.last_message = None
        self.socket.close()


def divide_message(message:str, max_bytes:int)->(int, int, list):
    """
    Divides 'message' into chunks of 'max_bytes'.
    Returns the total length of the message, the number of chunks 'n' and an array containing the chunks.
    """
    message_length = len(message.encode('utf-8'))

    n_chunks = ceil(message_length/max_bytes)

    chunks = []

    for i in range(n_chunks):
        init_index = i * max_bytes
        end_index = (i+1) * max_bytes

        if len(message[init_index:].encode('utf-8')) < max_bytes:
            chunks.append(message[init_index:])
        else:
            chunks.append(message[init_index:end_index])

    return message_length, n_chunks, chunks


def receive_full_message(conn, buff_size):
    '''
    The connection socket receives all the data until 'bytes_left' is zero,
    then returns the entire message
    '''
    data = conn.recv(buff_size)
    if data == None: #edge case for FIN
        return       

    message = data.decode()
    while conn.bytes_left!=0:
        data = conn.recv(buff_size)
        message += data.decode()
    
    return message