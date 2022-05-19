from welcome_server import WelcomeServer
from proxy_server import ProxyServer

address = ('localhost', 8889)
buffer_size = 64
end_of_message = "\r\n\r\n"

#server = WelcomeServer(address, buffer_size, end_of_message)
server = ProxyServer(address, buffer_size, end_of_message)

while True:
    server.wait_for_request()
    server.handle_request(verbose=True)
    