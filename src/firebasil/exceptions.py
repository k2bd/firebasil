class firebasilException(Exception):
    """
    Base exception for firebasil
    """


class RtdbException(firebasilException):
    """
    An issue with the realtime database
    """


class RtdbRequestException(RtdbException):
    """
    An issue with a network request to the realtime database
    """
