from TCPSocket import TCPSocket, receive_full_message

BUFF_SIZE=128
ADDRESS = ('localhost', 8888)
server = TCPSocket()
server.bind(ADDRESS)
server.settimeout(0.5)
print("server running in ", ADDRESS)

while True:
    print("waiting connection")
    connection, addr = server.accept()
    print("connection stablished with  {0}".format(addr))
    print("server connection seq number: ", connection.seq)

    while connection.destination_addr!= None:
        message = receive_full_message(connection, BUFF_SIZE)

        if message == None:
            continue

        print("received: ", message)
        connection.send_using_stop_and_wait(message.encode())
        print("message sent back")

    connection.close()
    print("connection closed")


        