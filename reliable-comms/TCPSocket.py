import socket
import sys
import random
from math import ceil
from collections import deque
from slidingWindow import SlidingWindow
from timerList import TimerList
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
        self.window_size = 3
        self.last_message = None
        self.destination_addr = None
        self.origin_addr = None
        self.timeout = 3
        self.last_ack_received = None
        self.possible_sequence_numbers = None

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
    
    def send(self, message, mode= "stop_and_wait"):
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)
        elif mode == "selective_repeat":
            self.send_using_selective_repeat(message)
        else:
            raise Exception("ERROR in TCPSocket, send(): Exhausted all possible modes")

    def recv(self, buff_size, mode= "stop_and_wait"):
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        elif mode == "selective_repeat":
            return self.recv_using_selective_repeat(message)
        else:
            raise Exception("ERROR in TCPSocket, recv(): Exhausted all possible modes")

    def send_using_stop_and_wait(self, message:bytes):
        
        message_length, n_chunks, message_chunks = divide_message(message.decode(), 64)
        #not_send = [True for chunk in message_chunks]   

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

    def send_all_window(self, data_window, timer_list):
        '''
        Builds segments from window, sends the data and enables timers
        '''
        for i in range(self.window_size):
            current_data = str(data_window.get_data(i))
            if current_data == None:
                break
            current_seq = data_window.get_sequence_number(i)
            current_segment = TCPHeader().build_string(0, 0, 0, current_seq, current_data)
            self.socket.sendto(current_segment.encode(), self.destination_addr)
            timer_list.start_timer(i)
            self.last_message = current_segment

            
    def send_using_go_back_n(self, message):
        counter=0
        #divide message and build sliding window
        message_length, n_chunks, message_chunks = divide_message(message.decode(), 64)
        data_list = [message_length] + message_chunks
        data_window = SlidingWindow(self.window_size, data_list, self.seq)
        self.possible_sequence_numbers = data_window.possible_sequence_numbers
        wnd_index = 0
        print("possible numbers are", data_window.possible_sequence_numbers)
        #timer setup
        timer_list = TimerList(self.timeout, self.window_size)
        t_index = 0

        #first window is sent
        self.send_all_window(data_window, timer_list)

        #socket is set to non blocking mode, to use TimerList instead
        self.socket.setblocking(False) #maybe change location of this piece of code

        while True:
            try:
                # en cada iteración vemos si nuestro timer hizo timeout
                timeouts = timer_list.get_timed_out_timers()
                # si hizo timeout reenviamos el último segmento
                if len(timeouts) > 0:
                    #all the window is sent back
                    self.send_all_window(data_window, timer_list)

                answer, _ = self.socket.recvfrom(self.buff_size)

            except BlockingIOError:
                counter+=1
                if counter%100000 == 0:
                    print(self.last_ack_received)
                # como nuestro socket no es bloqueante, si no llega nada entramos aquí y continuamos (hacemos esto en vez de usar threads)
                continue

            else:
                # si no entramos al except (y no hubo otro error) significa que llegó algo!
                # si la respuesta es un ack válido
                print("llegó algo")
                parsed_answer = TCPHeader().parse(answer.decode())
                print(parsed_answer)
                self.last_ack_received = parsed_answer
                print("el seq que tengo es ",data_window.get_sequence_number(0))
                if parsed_answer.seq == data_window.get_sequence_number(0): # esto se debe cambiar
                    # detenemos el timer
                    timer_list.stop_timer(0)

                    # actualizamos el segmento
                    data_window.move_window(1)
                    
                    #last element of window is current element
                    current_data = data_window.get_data(self.window_size-1)
                    
                    # si ya mandamos el mensaje completo tenemos current_data == None
                    if current_data == None:
                        self.update_seq_go_back_n()
                        print("send finished")
                        print("last message is: ", self.last_message)
                        print("window is:", data_window)
                        return

                    # si no, actualizamos el número de secuencia y mandamos el nuevo segmento
                    else:     
                        current_seq = data_window.get_sequence_number(self.window_size-1)
                        self.seq = current_seq
                        current_segment = TCPHeader().build_string(0, 0, 0, current_seq, current_data)
                        self.socket.sendto(current_segment.encode(), self.destination_addr)
                        self.last_message = current_segment
                        # y ponemos a correr de nuevo el timer
                        timer_list.start_timer(self.window_size-1)

    def resend_timed_out_segments(self, data_window:SlidingWindow, timeouts:TimerList):
        for index in timeouts.get_timed_out_timers():
            data = data_window.get_data(index)
            seq = data_window.get_sequence_number(index)
            segment = TCPHeader().build_string(0, 0, 0, seq, data)
            self.socket.sendto(segment.encode(), self.destination_addr)
            timeouts.start_timer(index)

    def move_timers(self, timeouts: TimerList, steps:int):     
        #deque object built from existing lists
        deque_starting_times = deque(timeouts.starting_times)
        deque_timer_list = deque(timeouts.timer_list)
        
        #deque rotate method moves the whole list to the left 'steps' times
        deque_starting_times.rotate(-steps)
        deque_timer_list.rotate(-steps)
        
        #reassign as lists to TimerList object
        timeouts.starting_times = list(deque_starting_times)
        timeouts.timer_list = list(deque_timer_list)

    def update_sender_window(self, data_window:SlidingWindow , timeouts:TimerList):
        '''
        Updates the sliding window of the sender in selective repeat.
        Also updates timers list in order to still match positions with the window
        Returns the steps the window moved.
        '''

        #indexes of window slots that still don't receive ack
        not_received_indexes = [index for (index,active_timer) in enumerate(timeouts.timer_list) if active_timer == True]
        
        if len(not_received_indexes) == 0:
            #all acks were received, the entire window is moved
            steps = self.window_size
            data_window.move_window(steps)
            
        else:
            steps = not_received_indexes[0]
            if steps > 0:
                data_window.move_window(steps)    # window moves as much as it can
                self.move_timers(timeouts, steps) # timers are moved to keep syncronization
        
        return steps           

    def update_current_data(self, data_window:SlidingWindow , timeouts:TimerList):
        indexes = []
        data_list = []
        for (index, has_timer) in enumerate(timeouts.timer_list):
            if not has_timer:
                data =  data_window.get_data(index)
                if data != None:
                    indexes.append(index)
                    data_list.append(data)
        if len(data_list)==1:
            return indexes[0], data_list[0]
        
        return indexes, data_list

    def send_using_selective_repeat(self, message):
        counter=0
        #divide message and build sliding window
        message_length, n_chunks, message_chunks = divide_message(message.decode(), 64)
        data_list = [message_length] + message_chunks
        data_window = SlidingWindow(self.window_size, data_list, self.seq)
        self.possible_sequence_numbers = data_window.possible_sequence_numbers
        
        #this maybe not
        wnd_index = 0
        t_index = 0

        print("possible numbers are", data_window.possible_sequence_numbers)

        timer_list = TimerList(self.timeout, self.window_size)
        

        #first window is sent
        self.send_all_window(data_window, timer_list)

        #socket is set to non blocking mode, to use TimerList instead
        self.socket.setblocking(False) 

        while True:
            try:
                timeouts = timer_list.get_timed_out_timers()
                
                if len(timeouts) > 0: #if a segment timed out, we send it again
                    self.resend_timed_out_segments(data_window,timeouts)

                answer, _ = self.socket.recvfrom(self.buff_size)

            except BlockingIOError:
                counter+=1
                if counter%100000 == 0:
                    print(self.last_ack_received)
                continue

            else:
                #print("llegó algo")
                ack = TCPHeader().parse(answer.decode())
                #print(ack)
                self.last_ack_received = ack
                #print("el seq que tengo es ",data_window.get_sequence_number(0))

                seqs_in_window = [data_window.get_sequence_number(i) for i in range(self.window_size)]

                if ack.seq in seqs_in_window:
                    #to which window slot belongs this ack
                    ack_window_index = seqs_in_window.index(ack.seq) 

                    timer_list.stop_timer(ack_window_index)

                    #here handle how much the window has to move
                    steps_window_moved = self.update_window(data_window, timeouts)
                    
                    if steps_window_moved == 0:
                        # window can't move and hasn't timed out yet. We must wait
                        continue

                    #here handle which data must be sent next
                    current_index, current_data = self.update_current_data(data_window, timeouts)
    
                    if current_data == None: # the message is completely sent
                        self.update_seq_go_back_n()
                        print("send finished")
                        print("last message is: ", self.last_message)
                        print("window is:", data_window)
                        return

                    # elif isinstance(current_data, list):
                    # #here handle the case where multiple messages are send
                    #     for i, data in enumerate(current_data):
                    #         current_seq = data_window.get_sequence_number(current_index[i])
                    #         self.seq = current_seq
                    #         current_segment = TCPHeader().build_string(0, 0, 0, current_seq, data)
                    #         self.socket.sendto(current_segment.encode(), self.destination_addr)
                    #         self.last_message = current_segment
                    #         # we start time again
                    #         timer_list.start_timer(current_index[i])
                    else:     
                        current_seq = data_window.get_sequence_number(current_index)
                        self.seq = current_seq
                        current_segment = TCPHeader().build_string(0, 0, 0, current_seq, current_data)
                        self.socket.sendto(current_segment.encode(), self.destination_addr)
                        self.last_message = current_segment
                        # we start time again
                        timer_list.start_timer(current_index)

        

    def valid_ack_seq(self, incoming_seq, current_seq):
        return incoming_seq == current_seq

    def update_seq_go_back_n(self):
        '''
        Function that updates the sequence
        number accordingly in Go Back N.
        It is assumed that the receiver has the same
        window_size value as the sender.
        '''
        try:
            current_seq_index = self.possible_sequence_numbers.index(self.seq)
            if current_seq_index == len(self.possible_sequence_numbers)-1:
                next_seq_index = 0
            else:
                next_seq_index = current_seq_index + 1

            self.seq = self.possible_sequence_numbers[next_seq_index]
        except:
            raise Exception("ERROR in TCPSocket, update_seq_go_back_n(): {0} is not a possible sequence number".format(self.seq))

    def calc_possible_sequence_numbers(self):
        self.possible_sequence_numbers = [self.seq + i for i in range(2 * self.window_size)]

    
    def recv_using_selective_repeat(self, buff_size):
        ...








    def recv_using_go_back_n(self, buff_size):

        counter = 0
        
        while self.bytes_left == 0: #new recv
            try:
                data, _ = self.socket.recvfrom(buff_size)
                parsed_data = TCPHeader().parse(data.decode())
               
                if parsed_data.fin == 1: #close connection
                    print("fin msg arrived: ", parsed_data)
                    self.recv_close()
                    return

                elif not self.valid_ack_seq(parsed_data.seq, self.seq): #repeated message
                    print("se reenvia mensaje. llegó {0} y tengo {1}".format(parsed_data.seq,self.seq))
                    print(parsed_data)
                    print("se enviará: ", self.last_message)
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                
                else: #new message
                    bytes_received = parsed_data.byte_len()
                    print(parsed_data)
                    message_length = int(parsed_data.data)
                    self.bytes_left = message_length
                    ack = TCPHeader().build_string(0, 1, 0, self.seq)
                    self.socket.sendto(ack.encode(), self.destination_addr)

                    self.calc_possible_sequence_numbers()
                    print(self.possible_sequence_numbers)

                    self.update_seq_go_back_n()
                    self.last_message = ack
                    self.last_ack_received = parsed_data

            except BlockingIOError:
                counter +=1
                if counter %100000 ==0:
                    print(self.last_ack_received)
                continue

        
        byte_cap = min(self.bytes_left, buff_size)

        acum_message =""
        while len(acum_message.encode()) < byte_cap:
            try:
                
                data, _ = self.socket.recvfrom(buff_size)
                header = TCPHeader().parse(data.decode())
                
                if header.fin == 1:
                    self.recv_close()
                    return

                elif not self.valid_ack_seq(header.seq, self.seq): #repeated message
                    self.socket.sendto(self.last_message.encode(), self.destination_addr)
                
                else: #new message
                    bytes_received = header.byte_len()
                    acum_message += header.data
                    ack = TCPHeader().build_string(0, 1, 0, self.seq) 
                    self.socket.sendto(ack.encode(), self.destination_addr)
                    
                    self.bytes_left -= len(header.data.encode())
                    self.update_seq_go_back_n()
                    self.last_message = ack
                    self.last_ack_received= header

            except BlockingIOError:
                #print("current bytes: ",len(acum_message.encode()))
                #print("bytes left: ", self.bytes_left)
                #print("byte cap: ", byte_cap)
                #print("last message: ", self.last_message)
                if counter%100000 == 0:
                    print(self.last_ack_received)
                if self.bytes_left <= 0:
                    break 
                continue
        
        return acum_message.encode()




    def recv_using_stop_and_wait(self, buff_size):
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

        self.socket.setblocking(True)
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
                        print("sent: ", fin_header)
                        print("received: ",fin_ack_header)
                        #raise FinError("Expected FIN + ACK, got {0} and {1}".format(fin_ack_header.fin, fin_ack_header.ack))
                        continue
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
        print("ATEMPTING TO CLOSE CONNECTION")
        print("------------------------------")
        self.socket.setblocking(True)
        self.seq += 1
        fin_ack_header = TCPHeader().build_string(0, 1, 1, self.seq)
        finalized = False
        while not finalized:
            try:       
                self.socket.sendto(fin_ack_header.encode(), self.destination_addr)
                print("sent: ", fin_ack_header)
                self.last_message = fin_ack_header

                ack, _ = self.socket.recvfrom(self.buff_size)
                ack_header = TCPHeader().parse(ack.decode())

                if ack_header.seq < self.seq: #repeated message

                    print("last message is:", self.last_message)
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


def receive_full_message(conn, buff_size, mode="stop_and_wait"):
    '''
    The connection socket receives all the data until 'bytes_left' is zero,
    then returns the entire message
    '''
    data = conn.recv(buff_size,mode= mode)
    if data == None: #edge case for FIN
        return       

    message = data.decode()
    while conn.bytes_left!=0:
        data = conn.recv(buff_size,mode= mode)
        message += data.decode()
    
    return message