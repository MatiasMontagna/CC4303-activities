from socketTCP import socketTCP

BUFF_SIZE=1024
ADDRESS = ('localhost', 8888)
server = socketTCP()
server.bind(ADDRESS)

print("server running in ", ADDRESS)
while True:
    print("waiting connection")
    addr = server.accept()
    print("connection stablished with  {0}".format(addr))
    print("server seq number: ", server.seq)

    while server.other_addr != None:  

        data = server.recv(BUFF_SIZE)

        if data !=None:
            print("received: ", data.decode())
            server.send(data)
        else:
            print("connection with {0} has ended".format(addr))
        