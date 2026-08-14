class BitrixError(Exception):
    """Base Bitrix exception"""

    pass


class BitrixRequestError(BitrixError):
    """HTTP or network error"""

    pass


class BitrixResponseError(BitrixError):
    """Bitrix returned error in JSON"""

    pass
