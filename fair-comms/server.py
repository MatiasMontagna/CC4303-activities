from TCPSocket import TCPSocket, receive_full_message

BUFF_SIZE=128
ADDRESS = ('localhost', 8888)

# MODE= "selective_repeat"
# MODE= "stop_and_wait"
MODE = "go_back_n"
server = TCPSocket()
server.bind(ADDRESS)
server.settimeout(2)
print("server running in ", ADDRESS)

while True:
    print("waiting connection")
    connection, addr = server.accept()
    print("connection stablished with  {0}".format(addr))
    print("server connection seq number: ", connection.seq)

    while connection.destination_addr!= None:
        message = receive_full_message(connection, BUFF_SIZE, mode= MODE)

        if message == None:
            continue

        print("received: ", message)
        print("my seq is:", connection.seq)
        connection.send(message.encode(), mode= MODE)
        print("message sent back")
        print("my seq is:", connection.seq)

    connection.close()
    print("connection closed")


        