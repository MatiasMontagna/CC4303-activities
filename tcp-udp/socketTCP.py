import socket
import random
import time
from errors import SeqError, NotConnectedException, FinError
from copy import deepcopy

SYN = b'SYN'
ACK = b'ACK'
FIN = b'FIN'

class socketTCP:
    '''
    simple TCP socket implementation that supports only one connection. Built using UDP socket
    '''

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0
        #self.ACK  #quizas despues puedo agregar aqui mis propios ACK y SYN
        self.buff_size = 1024
        self.other_addr = None
        self.other_msg = ""
    

    def bind(self,address):
        self.socket.bind(address)

    def send(self, data:bytearray):
        '''
        Sends data to another socketTCP with active connection.
        Returns the number of bytes sent.
        '''

        if self.other_addr == None:
            raise NotConnectedException("Tried to send data but no active connection was found")

        send_data = (data.decode() + "|>" + str(self.seq)).encode() # "|>" is the handle for the sequence number
        len_data = len(send_data)
        
        #socket waits for ACK or timeout(not implemented yet)
        succesful_send = False
        while not succesful_send:

            self.socket.sendto(send_data, self.other_addr)
            response_data, _ = self.socket.recvfrom(self.buff_size)
            #print(response_data.decode())
            incoming_seq = seq_from_data(response_data, ACK,sync=False)

            ##check if seq received matches what it should be
            if self.seq + len_data != incoming_seq:
                raise SeqError("Received {0}. Expected {1}".format(incoming_seq, self.seq + len_data))

            self.seq= incoming_seq
            succesful_send = True
        
        return len_data
        
        
    def recv(self, buff_size):
        '''
        receives message from other socketTCP that sent it using the `send` method 
        '''
        data,_ = self.socket.recvfrom(buff_size)

        if is_fin_segment(data): #close connection
            #1 FIN <==
            incoming_seq = seq_from_data(data, FIN)
            if incoming_seq != self.seq:
                raise SeqError("Received {0}. Expected {1}".format(incoming_seq, self.seq))

            #2 ==> FIN + ACK   
            msg = FIN.decode() + ACK.decode() + str(self.seq + 1)
            self.socket.sendto(msg.encode(), self.other_addr)

            #3 ACK <==
            final_data ,_=self.socket.recvfrom(self.buff_size)
            final_seq = seq_from_data(final_data, ACK)
            if final_seq != self.seq + 1:
                raise SeqError("Received {0}. Expected {1}".format(final_seq, self.seq + 1))  
            
            #remove active connection
            self.other_addr = None 

        else:
            bytes_received = len(data)

            incoming_seq = seq_from_data(data, None,sync=False) #todo

            if incoming_seq < self.seq: #segment duplicated           
                response = ACK.decode() + str(self.seq)
                self.socket.sendto(response.encode(), self.other_addr)

            else: #new segment        
                msg_bytes = msg_from_data(data)
                self.seq += bytes_received #seq number is updated
                response = ACK.decode() + "|>" +str(self.seq)
                self.socket.sendto(response.encode(), self.other_addr)
                return msg_bytes


    def listen(self):
        return

    def accept(self):
        '''
        Server side of the three way handshake
        '''

        #1 SYN <==
        data, other_addr = self.socket.recvfrom(self.buff_size)
        self.seq = seq_from_data(data, SYN)

        #2 ==> SYN + ACK
        msg = SYN.decode() + ACK.decode() + str(self.seq +1)
        self.socket.sendto(msg.encode(), other_addr)

        #3 ACK <==
        data, _ = self.socket.recvfrom(self.buff_size) 
        seq = seq_from_data(data, ACK)
        assert seq == self.seq+2 #client sent rigth seq number
        self.seq = seq
        self.other_addr = other_addr
        
        return other_addr

    def connect(self, address):
        '''
        Client side of the three way handshake
        '''

        #random seq is generated
        self.seq = random.randint(0, 100)
        
        #1 ==> SYN 
        msg = SYN.decode() + str(self.seq) 
        self.socket.sendto(msg.encode(), address)

        #2 SYN + ACK <==
        data, _ = self.socket.recvfrom(self.buff_size)
        code = (SYN.decode()+ACK.decode()).encode()
        received_seq = seq_from_data(data, code)
        assert self.seq + 1 == received_seq #server sent the rigth seq
        self.seq = received_seq

        #3 ==> ACK
        msg = ACK.decode() + str(self.seq+1)
        self.socket.sendto(msg.encode(), address)
        self.seq += 1

        self.other_addr = address
    
    def close(self):
        
        #1 ==> FIN
        end_connection = FIN.decode() + str(self.seq)
        self.socket.sendto(end_connection.encode(), self.other_addr)

        #2 FIN + ACK <== 
        data,_ = self.socket.recvfrom(self.buff_size)
        code = (FIN.decode()+ ACK.decode()).encode()
        received_seq = seq_from_data(data, code)

        if received_seq != self.seq + 1:
            raise SeqError("Received {0}. Expected {1}".format(received_seq, self.seq + 1))
        self.seq += 1

        #3 ==> ACK
        end_connection_confirmation = ACK.decode()+ str(self.seq)
        self.socket.sendto(end_connection_confirmation.encode(), self.other_addr)

        #reset variables, close socket
        self.other_addr = None
        self.socket.close()


def is_fin_segment(data:bytearray)->bool:
    '''
    reads incoming data to see if contains a FIN segment
    '''
    for i in range(len(FIN)):
        if data[i] != FIN[i]:
            return False
    
    return True

assert True == is_fin_segment(b"FIN34")
assert False == is_fin_segment(b"Hello world")


def msg_from_data(data:bytearray)->bytearray:
    '''
    retrieves the message bytes from the data, ignoring the seq number.
    '''

    msg_bytes = bytearray()
    delimiter = bytearray("|>".encode())
    delimiter_start = 0

    for i in range(len(data)):
        if data[i] == delimiter[0]:
            if data[i+1] == delimiter[1]:
                delimiter_start = i
                break

    for i in range(delimiter_start):
        msg_bytes.append(data[i])

    return msg_bytes

#tests
assert b"Hello world!" == msg_from_data(b"Hello world!|>99")
assert b"abc|d" == msg_from_data(b"abc|d|>99")

def seq_from_data(data: bytearray, code: bytearray, sync=True) -> int:
    '''
    retrieves the seq number from the data, ignoring 
    the bytes from `code` 
    '''

    seq = bytearray()
    if sync:  #in accept() and connect methods()
        

        for i in range(len(code)):
            if data[i] != code[i]:
                print("code not found at start of data")
                return

        for i in range(len(code), len(data)):
            seq.append(data[i])
  
    else:  #in recv method
        delimiter = bytearray("|>".encode())
        seq_start = 0
        for i in range(len(data)):
            if data[i] == delimiter[0]:
                if data[i+1] == delimiter[1]:
                    seq_start = i+2
                    break
        
        for i in range(seq_start, len(data)):
            seq.append(data[i])

    return int(seq.decode())

#tests
assert 435 == seq_from_data(b"SYN435", b"SYN")
assert 436 == seq_from_data(b"SYNACK436", b"SYNACK")
assert 837 == seq_from_data(b"ACK837", b"ACK")
assert 24 == seq_from_data(b"FIN24", FIN)

assert 44 == seq_from_data(b"Hello world|>44", None, sync= False)
assert 72 == seq_from_data(b"aaa|>72", None, sync= False)
