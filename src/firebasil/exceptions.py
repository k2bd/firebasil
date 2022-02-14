class FirebasilException(Exception):
    """
    Base exception for firebasil
    """


class RtdbException(FirebasilException):
    """
    An issue with the realtime database
    """


class RtdbRequestException(RtdbException):
    """
    An issue with a network request to the realtime database
    """


class RtdbListenerConnectionException(RtdbException):
    """
    Error connecting to the RTDB Listener
    """
