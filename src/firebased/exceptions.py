class FirebasedException(Exception):
    """
    Base exception for Firebased
    """


class RtdbException(FirebasedException):
    """
    An issue with the realtime database
    """


class RtdbRequestException(RtdbException):
    """
    An issue with a network request to the realtime database
    """
