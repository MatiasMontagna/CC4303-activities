from TCPSocket import TCPSocket, receive_full_message

BUFF_SIZE= 128

client = TCPSocket()
client.connect(('localhost', 8888))
client.settimeout(0.5)
print("connection succesful")
print("client seq number: ", client.seq)

file = open('lorem-ipsum.txt', 'r')
msg =file.read()

client.send(msg.encode())
print("sent: ", msg)
response = receive_full_message(client, BUFF_SIZE)
print("Got back: ", response)

client.close()

