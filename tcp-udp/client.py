from socketTCP2 import TCPSocket

BUFF_SIZE= 1024

client = TCPSocket()

client.connect(('localhost', 8888))
client.settimeout(3)
print("connection succesful")
print("client seq number: ", client.seq)
# msg = "Hello world"
# print("sent: ", msg)
# client.send(msg.encode())
# response = client.recv(BUFF_SIZE)

# print("Got back: ", response.decode())
# for i in range(10):
#     req = f"msg{i}"
#     print("sent: ",req)
#     client.send(req.encode())
#     resp = client.recv(BUFF_SIZE)
#     print("received:",resp.decode())

# client.close()
