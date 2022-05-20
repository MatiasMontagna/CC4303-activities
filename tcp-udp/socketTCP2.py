import socket
import sys
import random
import time
from errors import  DataSizeException,SeqError, NotConnectedException, FinError, SyncError


class TCPHeader:
    def __init__(self):
        self.syn: int = None
        self.ack: int = None
        self.fin: int = None
        self.seq: int = None
        self.data: str = None

    def __str__(self):
        s = "SYN: {0}, ACK: {1}, FIN: {2}, SEQ: {3}, DATA: {4}"
        return s.format(self.syn, self.ack, self.fin, self.seq, self.data)

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
        self.destination_addr = None
        self.origin_addr = None

    def settimeout(self, timeout_seconds):
        '''sets maximum waiting time (in seconds).'''
        self.socket.settimeout(timeout_seconds)

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
                header_bytes, _ = self.socket.recvfrom(self.buff_size)
                not_sent = False
            except KeyboardInterrupt: #enables ctr+c exit
                sys.exit()
            except: #timeout
                #socket sends the same message again
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
        self.socket.sendto(ack_msg.encode(), address)
        self.seq += 1
        self.destination_addr = address
    
    def accept(self):
        '''
        Server side of the three way handshake
        '''
        #1 SYN <==
        not_received = True
        while not_received:
            try:
                header_bytes, other_addr = self.socket.recvfrom(self.buff_size)
                not_received = False
            
            except KeyboardInterrupt: #enables ctr+c exit
                sys.exit()

            except:
                continue

        header = TCPHeader().parse(header_bytes.decode())
        if header.syn != 1:
            raise SyncError(f"Expected SYN but got {header.syn}")
        self.seq = header.seq

        #2 ==> SYN + ACK
        not_received = True
        msg = TCPHeader().build_string(1, 1, 0, self.seq + 1)
        while not_received:
            try:
                self.socket.sendto(msg.encode(), other_addr)

                #3 ACK <==
                data, _ = self.socket.recvfrom(self.buff_size)
                header = TCPHeader().parse(data.decode())
                if header.seq < self.seq+2: #mensaje repetido
                    continue

                not_received = False
            
            except KeyboardInterrupt: #enables ctr+c exit
                sys.exit()

            except:
                continue

        
        if header.ack != 1:
            raise SyncError(f"Expected ACK but got {header.ack}")
        if header.seq != self.seq+2:
            raise SeqError("Received {0}. Expected {1}".format(header.seq, self.seq + 2))

        self.seq = header.seq
        self.destination_addr = other_addr
        return self, self.destination_addr