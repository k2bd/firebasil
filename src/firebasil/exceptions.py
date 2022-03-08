class FirebasilException(Exception):
    """
    Base exception for firebasil
    """


class AuthException(FirebasilException):
    """
    An issue with auth
    """


class AuthRequestException(AuthException):
    """
    An issue with a network request to auth
    """


class RtdbException(FirebasilException):
    """
    An issue with the realtime database
    """


class RtdbRequestException(RtdbException):
    """
    An issue with a network request to the realtime database
    """


class RtdbEventStreamException(RtdbException):
    """
    Error connecting to the RTDB Listener
    """
