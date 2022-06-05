from TCPSocket import TCPSocket, receive_full_message

BUFF_SIZE= 128
#MODE = "selective_repeat"
#MODE = "stop_and_wait"
MODE = "go_back_n"

client = TCPSocket()
client.connect(('localhost', 8888))
client.settimeout(2)
print("connection succesful")
print("client seq number: ", client.seq)

file = open('lorem-ipsum.txt', 'r')
msg =file.read()

client.send(msg.encode(),mode=MODE)
print("sent: ", msg)
print("seq is: ",client.seq)
response = receive_full_message(client, BUFF_SIZE, mode=MODE)
print("Got back: ", response)
print("seq is: ",client.seq)
client.close()
print("connection closed")

