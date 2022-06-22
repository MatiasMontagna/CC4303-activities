class IPHeader:
    def __init__(self):
        self.ip_address = None
        self.port: int = None
        self.ttl: int = None
        self.message: str = None

    def __str__(self):
        s = "{0},{1},{2},{3}"
        return s.format(self.ip_address, self.port, self.ttl, self.message)
    
    def byte_len(self):
        return len(self.__str__().encode())

    def encode(self):
        return self.__str__().encode()

    @staticmethod
    def parse(message: str):
        """Parses a [IP ADDRESS],[PORT],[TTL],[MESSAGE] string and returns a Header object."""

        header_list = message.split(",")
        header = IPHeader()
        header.ip_address = header_list[0]
        header.port = int(header_list[1])
        header.ttl = int(header_list[2])
        header.message = header_list[3]

        return header
    
    @staticmethod
    def build(address: tuple, ttl:int, message: str):
        '''Builds a Header object from the parameters given.'''
        header = IPHeader()
        header.ip_address, header.port = address
        header.ttl = ttl
        header.message = message
       
        return header


header = IPHeader().parse("127.0.0.1,8881,255,Hello world")
assert "127.0.0.1" == header.ip_address
assert 8881 == header.port
assert "Hello world" == header.message
assert 255 == header.ttl
assert "127.0.0.1,8881,254,Hello world" == IPHeader().build(("127.0.0.1",8881), 254,"Hello world").__str__()