class IPHeader:
    def __init__(self):
        self.ip_address = None
        self.port: int = None
        self.ttl: int = None
        self.id: int = None
        self.offset = None
        self.size = None
        self.flag = None
        self.message: str = None

    def __str__(self):
        s = "{0},{1},{2},{3},{4},{5},{6},{7}"
        return s.format(self.ip_address, self.port, self.ttl, self.id, self.offset, self.size, self.flag, self.message)
    
    def byte_len(self):
        return len(self.__str__().encode())

    def encode(self):
        return self.__str__().encode()

    @staticmethod
    def parse(message: str):
        """Parses a [IP ADDRESS],[PORT],[TTL],[ID],[OFFSET],[SIZE],[FLAG],[MESSAGE] string and returns a Header object."""

        header_list = message.split(",")
        header = IPHeader()
        header.ip_address = header_list[0]
        header.port = int(header_list[1])
        header.ttl = int(header_list[2])
        header.id = int(header_list[3])
        header.offset = int(header_list[4])
        header.size = int(header_list[5])
        header.flag = int(header_list[6])
        header.message = header_list[7]

        return header
    
    @staticmethod
    def build(address: tuple, ttl:int,id, offset, size, flag ,message: str):
        '''Builds a Header object from the parameters given.'''
        header = IPHeader()
        header.ip_address, header.port = address
        header.ttl = ttl
        header.id = id
        header.offset = offset
        header.size = size
        header.flag = flag
        header.message = message
        
        return header


header = IPHeader().parse("127.0.0.1,8881,255,1,400,200,0,Hello world")
assert "127.0.0.1" == header.ip_address
assert 8881 == header.port
assert 1 == header.id
assert 400 == header.offset
assert 200 == header.size
assert 0 == header.flag
assert "Hello world" == header.message
assert 255 == header.ttl
assert "127.0.0.1,8881,254,2,500,300,1,Hello world" == IPHeader().build(("127.0.0.1",8881), 254, 2, 500, 300, 1,"Hello world").__str__()