import ipaddress
import math
import re

from ax_interface import constants


def oid2tuple(oid_str, dot_prefix=True):
    """
    >>> oid2tuple('.1.3.6.1.4.1.6027.3.10.1.2.9')
    (1, 3, 6, 1, 4, 1, 6027, 3, 10, 1, 2, 9)
    >>> oid2tuple('1.2.3.4')
    (1, 3, 6, 1, 1, 2, 3, 4)
    >>> oid2tuple('1.2.3.4', dot_prefix=False)
    (1, 2, 3, 4)

    :param oid_str: dot-delimited OID string
    :param dot_prefix: if True, the absence of a leading dot will prepend the internet prefix to the OID.
    :return: the OID (as tuple)
    """
    if not oid_str:
        return ()

    # Validate OID before attempting to process.
    if not is_valid_oid(oid_str, dot_prefix):
        raise ValueError("Invalid OID string.")

    sub_ids = ()
    if dot_prefix:
        if oid_str.startswith('.'):
            # the OID starts with a '.' so, we will interpret it literally.
            oid_str = oid_str[1:]
        else:
            # no '.', prepend the internet prefix
            sub_ids = constants.INTERNET_PREFIX

    sub_ids += tuple(int(sub_id) for sub_id in oid_str.split('.'))

    return sub_ids


def is_valid_oid(oid_str, dot_prefix=True):
    """
    >>> is_valid_oid('2')
    True
    >>> is_valid_oid('2.')
    False
    >>> is_valid_oid('.2')
    True
    >>> is_valid_oid('.2.2')
    True
    >>> is_valid_oid('.2.2.')
    False
    >>> is_valid_oid('.2.2.3', False)
    False

    A valid OID contains:
    1. zero or one leading '.' (dot);
    2. any number of groups with variable length decimals followed by a '.' (dot);
    3. concluded by a variable length decimal.
    :param oid_str: string to validate
    :return: boolean indicating if the oid is valid.
    """
    oid_regex = r'((\d+\.)*\d+)'
    if dot_prefix:
        oid_regex = r'\.?' + oid_regex
    m = re.match(oid_regex, oid_str)
    return m is not None and m.group() == oid_str


def pad4(length):
    """
    >>> pad4(9)
    3
    >>> pad4(20)
    0

    :param length:
    :return:
    """
    return -(length % -4)


def pad4bytes(length):
    """
    >>> pad4bytes(11)
    b\'\\x00\'
    >>> pad4bytes(40)
    b\'\'

    :param length:
    :return:
    """
    return pad4(length) * constants.RESERVED_ZERO_BYTE

def mac_decimals(mac):
    """
    >>> mac_decimals("52:54:00:57:59:6A")
    (82, 84, 0, 87, 89, 106)
    """
    return tuple(int(h, 16) for h in mac.split(":"))

def ip2byte_tuple(ip):
    """
    >>> ip2byte_tuple("192.168.1.253")
    (192, 168, 1, 253)
    >>> ip2byte_tuple("2001:db8::3")
    (32, 1, 13, 184, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3)
    """
    return tuple(i for i in ipaddress.ip_address(ip).packed)


def get_next_update_interval(execution_time, static_frequency):
    """
    >>> get_next_update_interval(0.4, 5)
    5
    >>> get_next_update_interval(0.87, 5)
    9
    >>> get_next_update_interval(18.88, 5)
    60


    :param static_frequency: Static frequency, generally use default value 5
    :param execution_time: The execution time of the updater
    :return: the interval before next update

    We expect the rate of 'update interval'/'update execution time' >= UPDATE_FREQUENCY_RATE(10)
    Because we're using asyncio/Coroutines, the update execution blocks SNMP proxy service and other updaters.
    Generally we expect the update to be quick and the execution time/interval time < 0.25
    Given the static_frequency == 5,
    if the execution_time < 0.5,
    the update interval is(for example) 1.1s
    It sleeps 1.1s * 10 = 11s before run next update

    """
    frequency_based_on_execution_time = math.ceil(execution_time * constants.UPDATE_FREQUENCY_RATE)
    frequency_based_on_execution_time = min(frequency_based_on_execution_time, constants.MAX_UPDATE_INTERVAL)

    return max(static_frequency, frequency_based_on_execution_time)
