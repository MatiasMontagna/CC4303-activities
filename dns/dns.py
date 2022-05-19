import socket
from utils import find_domain
from dnslib import DNSRecord

port = 5352
ip = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))

cache = {}

while True:
    #wait for connection
    data, addr = sock.recvfrom(512)
    dns_req = DNSRecord.parse(data)
    
    #we get the domain and procceed to look for its IP address
    domain = dns_req.get_q().get_qname().__str__() 
    answer_data = find_domain(domain, cache, debug=True)

    #we build the reply with the answer, and then send it
    a = dns_req.reply()
    a.add_answer(answer_data)
    sock.sendto(bytes(a.pack()), addr)
