def mac_decimals(mac):
    """
    >>> mac_decimals("52:54:00:57:59:6A")
    (82, 84, 0, 87, 89, 106)
    """
    return tuple(int(h, 16) for h in mac.split(":"))

