import time
from functools import wraps

import redis
from redis import RedisError

from swsssdk import logger
from swsssdk.exceptions import UnavailableDataError, MissingClientError

BLOCKING_ATTEMPT_ERROR_THRESHOLD = 10
BLOCKING_ATTEMPT_SUPPRESSION = BLOCKING_ATTEMPT_ERROR_THRESHOLD + 5


def blockable(f):
    """
    "blocking" decorator for Redis accessor methods. Wrapped functions that specify kwarg 'blocking'
    will wait for the specified accessor to return with data.::

        class SonicV2Connector:
            @blockable
            def keys(self, db_name):
                # ...

        # call with:
        db = SonicV2Connector()
        # ...
        db.keys('DATABASE', blocking=True)

    """

    @wraps(f)
    def wrapped(inst, db_name, *args, **kwargs):

        blocking = kwargs.pop('blocking', False)
        attempts = 0
        while True:
            try:
                ret_data = f(inst, db_name, *args, **kwargs)
                inst._unsubscribe_keyspace_notification(db_name)
                return ret_data
            except UnavailableDataError as e:
                if blocking:
                    if db_name in inst.keyspace_notification_channels:
                        result = inst._unavailable_data_handler(db_name, e.data)
                        if result:
                            continue # received updates, try to read data again
                        else:
                            inst._unsubscribe_keyspace_notification(db_name)
                            raise    # No updates was received. Raise exception
                    else: # Subscribe to updates and try it again (avoiding race condition)
                        inst._subscribe_keyspace_notification(db_name)
                else:
                    return None
            except redis.exceptions.ResponseError:
                """
                A response error indicates that something is fundamentally wrong with the request itself.
                Retrying the request won't pass unless the schema itself changes. In this case, the error
                should be attributed to the application itself. Re-raise the error.
                """
                logger.exception("Bad DB request [{}:{}]{{ {} }}".format(db_name, f.__name__, str(args)))
                raise
            except (redis.exceptions.RedisError, OSError):
                attempts += 1
                inst._connection_error_handler(db_name)
                msg = "DB access failure by [{}:{}]{{ {} }}".format(db_name, f.__name__, str(args))
                if BLOCKING_ATTEMPT_ERROR_THRESHOLD < attempts < BLOCKING_ATTEMPT_SUPPRESSION:
                    # Repeated access failures implies the database itself is unhealthy.
                    logger.exception(msg=msg)
                else:
                    logger.warning(msg=msg)

    return wrapped


class DBRegistry(dict):
    def __getitem__(self, item):
        if item not in self:
            raise MissingClientError("No client connected for db_name '{}'".format(item))
        return dict.__getitem__(self, item)


class DBInterface(object):
    REDIS_HOST = '127.0.0.1'
    """
    SONiC does not use a password-protected database. By default, Redis will only allow connections to unprotected
    DBs over the loopback ip.
    """

    REDIS_PORT = 6379
    """
    SONiC uses the default port.
    """

    REDIS_UNIX_SOCKET_PATH = "/var/run/redis/redis.sock"
    """
    SONiC uses the default unix socket.
    """

    CONNECT_RETRY_WAIT_TIME = 10
    """
    Wait period in seconds before attempting to reconnect to Redis.
    """

    DATA_RETRIEVAL_WAIT_TIME = 3
    """
    Wait period in seconds to wait before attempting to retrieve missing data.
    """

    PUB_SUB_NOTIFICATION_TIMEOUT = 10.0  # seconds
    """
    Time to wait for any given message to arrive via pub-sub.
    """

    PUB_SUB_MAXIMUM_DATA_WAIT = 60.0  # seconds
    """
    Maximum allowable time to wait on a specific pub-sub notification.
    """

    KEYSPACE_PATTERN = '__key*__:*'
    """
    Pub-sub keyspace pattern
    """

    KEYSPACE_EVENTS = 'KEA'
    """
    In Redis, by default keyspace events notifications are disabled because while not
    very sensible the feature uses some CPU power. Notifications are enabled using
    the notify-keyspace-events of redis.conf or via the CONFIG SET.
    In order to enable the feature a non-empty string is used, composed of multiple characters,
    where every character has a special meaning according to the following table:
    K - Keyspace events, published with __keyspace@<db>__ prefix.
    E - Keyevent events, published with __keyevent@<db>__ prefix.
    g - Generic commands (non-type specific) like DEL, EXPIRE, RENAME, ...
    $ - String commands
    l - List commands
    s - Set commands
    h - Hash commands
    z - Sorted set commands
    x - Expired events (events generated every time a key expires)
    e - Evicted events (events generated when a key is evicted for maxmemory)
    A - Alias for g$lshzxe, so that the "AKE" string means all the events.
    ACS Redis db mainly uses hash, therefore h is selected.
    """

    def __init__(self, **kwargs):

        super(DBInterface, self).__init__()

        # Store the arguments for redis client
        self.redis_kwargs = kwargs
        if len(self.redis_kwargs) == 0:
            self.redis_kwargs['unix_socket_path'] = self.REDIS_UNIX_SOCKET_PATH

        # For thread safety as recommended by python-redis
        # Create a separate client for each database
        self.redis_clients = DBRegistry()

        # record db_name to db_id mapping on local
        self.redis_db_map = {}

        # Create a channel for receiving needed keyspace event
        # notifications for each client
        self.keyspace_notification_channels = DBRegistry()

    def connect(self, db_id, db_name, retry_on=True):
        """
        :param db_id: database id to connect to
        :param db_name: database name to connect to
        :param retry_on: if ``True`` -- will attempt to connect continuously.
        if ``False``, only one attempt will be made.
        """
        if retry_on:
            self._persistent_connect(db_id, db_name)
        else:
            self._onetime_connect(db_id, db_name)

    def _onetime_connect(self, db_id, db_name):
        """
        Connect to database id.
        """
        if db_id is None:
            raise ValueError("No database ID configured for '{}'".format(db_id))

        if db_name is None:
            raise ValueError("No database Name configured for '{}'".format(db_name))

        if db_name not in self.redis_clients.keys():
            self.redis_db_map[db_name] = db_id
            client = redis.StrictRedis(db=db_id, **self.redis_kwargs)

            # Enable the notification mechanism for keyspace events in Redis
            client.config_set('notify-keyspace-events', self.KEYSPACE_EVENTS)
            self.redis_clients[db_name] = client

    def _persistent_connect(self, db_id, db_name):
        """
        Keep reconnecting to Database 'db_id' until success
        """
        while True:
            try:
                self._onetime_connect(db_id, db_name)
                return
            except RedisError:
                t_wait = self.CONNECT_RETRY_WAIT_TIME
                logger.warning("Connecting to DB '{} {}' failed, will retry in {}s".format(db_id, db_name, t_wait))
                self.close(db_name)
                time.sleep(t_wait)

    def close(self, db_name):
        """
        Close all client(s) / keyspace channels.
        :param db_name: DB to disconnect from.
        """
        if db_name in self.redis_clients:
            self.redis_clients[db_name].connection_pool.disconnect()
            del self.redis_clients[db_name]
        if db_name in self.keyspace_notification_channels:
            self.keyspace_notification_channels[db_name].close()
            del self.keyspace_notification_channels[db_name]

    def _subscribe_keyspace_notification(self, db_name):
        """
        Subscribe the chosent client to keyspace event notifications
        """
        logger.debug("Subscribe to keyspace notification")
        client = self.redis_clients[db_name]
        pubsub = client.pubsub()
        pubsub.psubscribe(self.KEYSPACE_PATTERN)
        self.keyspace_notification_channels[db_name] = pubsub

    def _unsubscribe_keyspace_notification(self, db_name):
        """
        Unsubscribe the chosent client from keyspace event notifications
        """
        if db_name in self.keyspace_notification_channels:
            logger.debug("Unsubscribe from keyspace notification")
            self.keyspace_notification_channels[db_name].close()
            del self.keyspace_notification_channels[db_name]

    def get_redis_client(self, db_name):
        """
        :param db_name: Name of the DB to query
        :return: The Redis client instance.
        """
        return self.redis_clients[db_name]

    def publish(self, db_name, channel, message):
        """
        Publish message via the channel
        """
        client  = self.redis_clients[db_name]
        return client.publish(channel, message)

    def expire(self, db_name, key, timeout_sec):
        """
        Set a timeout on a key
        """
        client = self.redis_clients[db_name]
        return client.expire(key, timeout_sec)

    def exists(self, db_name, key):
        """
        Check if a key exist in the db
        """
        client = self.redis_clients[db_name]
        return client.exists(key)

    @blockable
    def keys(self, db_name, pattern='*'):
        """
        Retrieve all the keys of DB %db_name
        """
        client = self.redis_clients[db_name]
        keys = client.keys(pattern=pattern)
        if not keys:
            message = "DB '{}' is empty!".format(db_name)
            logger.warning(message)
            raise UnavailableDataError(message, b'hset')
        else:
            return keys

    @blockable
    def get(self, db_name, _hash, key):
        """
        Retrieve the value of Key %key from Hashtable %hash
        in Database %db_name

        Parameter %blocking indicates whether to wait
        when the query fails
        """
        client = self.redis_clients[db_name]
        val = client.hget(_hash, key)
        if not val:
            message = "Key '{}' field '{}' unavailable in database '{}'".format(_hash, key, db_name)
            logger.warning(message)
            raise UnavailableDataError(message, _hash)
        else:
            # redis only supports strings. if any item is set to string 'None', cast it back to the appropriate type.
            return None if val == b'None' else val

    @blockable
    def get_all(self, db_name, _hash):
        """
        Get Hashtable %hash from DB %db_name

        Parameter %blocking indicates whether to wait
        if the hashtable has not been created yet
        """
        client = self.redis_clients[db_name]
        table = client.hgetall(_hash)
        if not table:
            message = "Key '{}' unavailable in database '{}'".format(_hash, db_name)
            logger.warning(message)
            raise UnavailableDataError(message, _hash)
        else:
            # redis only supports strings. if any item is set to string 'None', cast it back to the appropriate type.
            return {k: None if v == b'None' else v for k, v in table.items()}

    @blockable
    def set(self, db_name, _hash, key, val):
        """
        Add %(key, val) to Hashtable %hash in DB %db_name
        Parameter %blocking indicates whether to retry in case of failure
        """
        client = self.redis_clients[db_name]
        return client.hset(_hash, key, val)

    @blockable
    def delete(self, db_name, key):
        """
        Delete %key from DB %db_name
        Parameter %blocking indicates whether to retry in case of failure
        """
        client = self.redis_clients[db_name]
        return client.delete(key)

    @blockable
    def delete_all_by_pattern(self, db_name, pattern):
        """
        Delete all keys which match %pattern from DB %db_name
        Parameter %blocking indicates whether to retry in case of failure
        """
        client = self.redis_clients[db_name]
        keys = client.keys(pattern)
        for key in keys:
            client.delete(key)

    def _unavailable_data_handler(self, db_name, data):
        """
        When the queried config is not available in Redis--wait until it is available.
        Two timeouts are at work here:
        1. Notification timeout - how long to wait before giving up on receiving any given pub-sub message.
        2. Max data wait - swsssdk-specific. how long to wait for the data to populate (in absolute time)
        """
        start = time.time()
        logger.debug("Listening on pubsub channel '{}'".format(db_name))
        while time.time() - start < self.PUB_SUB_MAXIMUM_DATA_WAIT:
            msg = self.keyspace_notification_channels[db_name].get_message(timeout=self.PUB_SUB_NOTIFICATION_TIMEOUT)
            if msg is not None and msg.get('data') == data:
                logger.info("'{}' acquired via pub-sub. Unblocking...".format(data, db_name))
                # Wait for a "settling" period before releasing the wait.
                time.sleep(self.DATA_RETRIEVAL_WAIT_TIME)
                return True

        logger.warning("No notification for '{}' from '{}' received before timeout.".format(data, db_name))
        return False

    def _connection_error_handler(self, db_name):
        """
        In the event Redis is unavailable, close existing connections, and try again.
        """
        logger.warning('Could not connect to Redis--waiting before trying again.')
        self.close(db_name)
        time.sleep(self.CONNECT_RETRY_WAIT_TIME)
        self.connect(self.redis_db_map[db_name], db_name, True)
