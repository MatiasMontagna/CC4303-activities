class Header:
    def __init__(self):
        self.ip_address = None
        self.port: int = None
        self.message: str = None

    def __str__(self):
        s = "{0},{1},{2}"
        return s.format(self.ip_address, self.port, self.message)
    
    def byte_len(self):
        return len(self.__str__().encode())

    def encode(self):
        return self.__str__().encode()

    @staticmethod
    def parse(message: str):
        """Parses a [IP ADDRESS],[PORT],[MESSAGE] string and returns a Header object."""

        header_list = message.split(",")
        header = Header()
        header.ip_address = header_list[0]
        header.port = int(header_list[1])
        header.message = header_list[2]

        return header
    
    @staticmethod
    def build(address: tuple, message: str):
        '''Builds a Header object from the parameters given.'''
        header = Header()
        header.ip_address, header.port = address
        header.message = message
       
        return header


header = Header().parse("127.0.0.1,8881,Hello world")
assert "127.0.0.1" == header.ip_address
assert 8881 == header.port
assert "Hello world" == header.message
assert "127.0.0.1,8881,Hello world" == Header().build(("127.0.0.1",8881), "Hello world").__str__()