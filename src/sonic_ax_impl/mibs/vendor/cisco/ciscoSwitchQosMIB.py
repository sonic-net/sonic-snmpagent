from enum import unique, Enum
from bisect import bisect_right

from sonic_ax_impl import mibs
from ax_interface import MIBMeta, ValueType, MIBUpdater, MIBEntry, SubtreeMIBEntry
from ax_interface.encodings import ObjectIdentifier

# Maps queue stat counters names to SNMP sub-identifiers.
CounterNames = {
    1 : 'ucastSentPkts',
    2 : 'ucastSentBytes',
    3 : 'mcastSentPkts',
    4 : 'mcastSentBytes',
    5 : 'ucastDroppedPkts',
    6 : 'ucastDroppedBytes',
    7 : 'mcastDroppedPkts',
    8 : 'mcastDroppedBytes' }

# Maps SNMP queue stat counters to SAI counters
SaiCounterNameMap = {
    'ucastSentPkts'     : b'SAI_QUEUE_STAT_PACKETS',
    'ucastSentBytes'    : b'SAI_QUEUE_STAT_BYTES',
    'mcastSentPkts '    : b'SAI_QUEUE_STAT_PACKETS',
    'mcastSentBytes'    : b'SAI_QUEUE_STAT_BYTES',
    'ucastDroppedPkts'  : b'SAI_QUEUE_STAT_DROPPED_PACKETS',
    'ucastDroppedBytes' : b'SAI_QUEUE_STAT_DROPPED_BYTES',
    'mcastDroppedPkts'  : b'SAI_QUEUE_STAT_DROPPED_PACKETS',
    'mcastDroppedBytes' : b'SAI_QUEUE_STAT_DROPPED_BYTES' }

# Maps queue stat counters names to required SAI type of queue
SaiCounterTypeMap = {
     'ucastSentPkts'     : b'SAI_QUEUE_TYPE_UNICAST',
     'ucastSentBytes'    : b'SAI_QUEUE_TYPE_UNICAST',
     'mcastSentPkts '    : b'SAI_QUEUE_TYPE_MULTICAST',
     'mcastSentBytes'    : b'SAI_QUEUE_TYPE_MULTICAST',
     'ucastDroppedPkts'  : b'SAI_QUEUE_TYPE_UNICAST',
     'ucastDroppedBytes' : b'SAI_QUEUE_TYPE_UNICAST',
     'mcastDroppedPkts'  : b'SAI_QUEUE_TYPE_MULTICAST',
     'mcastDroppedBytes' : b'SAI_QUEUE_TYPE_MULTICAST' }

class DirectionTypes(int, Enum):
    """
    Queue direction types
    """
    INGRESS = 1
    EGRESS = 2

class QueueStatUpdater(MIBUpdater):
    """
    Class to update the info from Counter DB and to handle the SNMP request
    """
    def __init__(self):
        """
        init the updater
        """
        super().__init__()
        self.db_conn = mibs.init_db()
        self.reinit_data()

        self.lag_name_if_name_map = {}
        self.if_name_lag_name_map = {}
        self.oid_lag_name_map = {}

    def reinit_data(self):
        """
        Subclass update interface information
        """
        self.port_queues_map, self.queue_stat_map = mibs.init_sync_d_queue_tables(self.db_conn)

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each queue.
        """
        for queue_key, sai_id in self.port_queues_map.items():
            queue_stat_name = mibs.queue_table(sai_id)
            queue_stat = self.db_conn.get_all(mibs.COUNTERS_DB, queue_stat_name, blocking=False)
            if queue_stat is not None:
                self.queue_stat_map[queue_stat_name] = queue_stat

        self.lag_name_if_name_map, \
        self.if_name_lag_name_map, \
        self.oid_lag_name_map = mibs.init_sync_d_lag_tables(self.db_conn)

    def get_next(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the next sub id.
        """

        #User should specify the ifindex, queue direction and index
        if (sub_id is None) or (len(sub_id) < 3):
            return None

        last_index = len(sub_id) - 1
        counter_id = sub_id[last_index]
        right = counter_id + 1

        if right >= len(CounterNames):
            return None

        return (sub_id[0], sub_id[1], sub_id[2], right)


    def _get_counter(self, if_index, queue_index, queue_counter_id):
        """
        :param sub_id: The interface OID.
        :param counter_name: the redis table (either IntEnum or string literal) to query.
        :return: the counter for the respective sub_id/table.
        """
        queue_oid = ''

        try:
            key = mibs.queue_key(if_index, queue_index)
            queue_oid = self.port_queues_map[key]
        except KeyError as e:
            mibs.logger.warning("queue map has no oid for {} port, {} queue.".format(if_index, queue_index))
            return None

        queue_stat_table_name = mibs.queue_table(queue_oid)
        queue_type = ''

        try:
            queue_type = self.queue_stat_map[queue_stat_table_name][b'SAI_QUEUE_ATTR_TYPE']
        except KeyError as e:
            mibs.logger.warning("unable to get the queue type for {} queue of {} port.".format(queue_index, if_index))
            return None

        try:
            counter_snmp_name = CounterNames[queue_counter_id]
            counter_sai_name = SaiCounterNameMap[counter_snmp_name]
            counter_sai_type = SaiCounterTypeMap[counter_snmp_name]
        except KeyError as e:
            mibs.logger.warning("unable to map the sai counter for {} counter of {} queue. {} port.".format(queue_counter_id, queue_index, if_index))
            return None

        # queue has different type then requested counter
        if queue_type != counter_sai_type:
            return None

        counter_value = ''

        try:
            counter_value = self.queue_stat_map[queue_stat_table_name][counter_sai_name]
        except KeyError as e:
            mibs.logger.warning("queue stat map has no {} table or {} counter in described table.".format(queue_stat_table_name, counter_sai_name))
            return None

        counter_value = int(counter_value)

        return counter_value

    def handleStatRequest(self, sub_id):
        """
        :param sub_id: The 1-based sub-identifier query.
        :return: the counter for the respective sub_id/table.
        """
        # if_index, if_direction, queue_index and counter id should be passed

        if len(sub_id) != 4:
            return

        if_index = sub_id[0]
        if_direction = sub_id[1]
        queue_index = int(sub_id[2]) - 1
        queue_counter_id = sub_id[3]

        # Currently, Sonic supports only egress queues
        if if_direction != DirectionTypes.EGRESS:
            return

        if if_index in self.oid_lag_name_map:
            counter_value = 0
            for lag_member in self.lag_name_if_name_map[self.oid_lag_name_map[if_index]]:
                counter_value += self._get_counter(mibs.get_index(lag_member), queue_index, queue_counter_id)

            return counter_value
        else:
            return self._get_counter(if_index, queue_index, queue_counter_id)


class csqIfQosGroupStatsTable(metaclass=MIBMeta, prefix='.1.3.6.1.4.1.9.9.580.1.5.5'):
    """
    'csqIfQosGroupStatsTable' http://oidref.com/1.3.6.1.4.1.9.9.580.1.5.5
    """

    queue_updater = QueueStatUpdater()

    # csqIfQosGroupStatsTable = '1.3.6.1.4.1.9.9.580.1.5.5'
    # csqIfQosGroupStatsEntry = '1.3.6.1.4.1.9.9.580.1.5.5.1.4'

    queue_stat_request = \
        SubtreeMIBEntry('1.4', queue_updater, ValueType.INTEGER, queue_updater.handleStatRequest)
