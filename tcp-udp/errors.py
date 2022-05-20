class FinError(Exception):
    """Raised when end of communication between two socketTCP fails"""
    pass

class SeqError(Exception):
    "Raised when seq's don't match"
    pass

class SyncError(Exception):
    """Raised when syncronization between two TCPSocket's fails"""
    pass

class NotConnectedException(Exception):
    """Raised when attempting to send data without being connected to a socketTCP"""
    pass

class DataSizeException(Exception):
    """Raised when attempting to send packet data that surpasses 64 bytes"""