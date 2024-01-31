import multiprocessing
from functools import cmp_to_key

import device_info
import message_formatter
import sender as b_send
import util

BUFFER_SIZE = 4096


class OrderedMulticastListener(multiprocessing.Process):
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 device_info_dynamic: device_info.DeviceInfoDynamic,
                 receive_queue: multiprocessing.Queue,
                 deliver_queue: multiprocessing.Queue,
                 delivered_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy,
                 lock):
        super(OrderedMulticastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.r_deliver_queue = receive_queue
        self.o_deliver_queue = deliver_queue
        self.delivered_queue = delivered_queue
        self.shared_dict = shared_dict
        self.lock = lock
        self.isRunning = True
        self.hold_back_queue = []

    def run(self):
        print("Listening for reliable multicast delivery")
        self.consistent_order_listen()

    def consistent_order_listen(self):
        # is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.update_device_info_dynamic()
                # receive reliable multicast delivery
                message = self.r_deliver_queue.get()
                # add to hold back queue
                self.hold_back_queue.append(message)

                self.hold_back_queue = sorted(self.hold_back_queue, key=cmp_to_key(util.compare_vector_clocks))
                deliver_list = []
                # check if we can deliver the message or if we need to hold the changes back in the queue a bit longer
                for entry in self.hold_back_queue.copy():
                    filename, vector_clock, temp_filename, sender_id, message_type, original_sender_id = entry
                    # hold back check
                    if not self.vector_clock_condition(vector_clock, original_sender_id):
                        print("Holding back message in hold back queue")
                        b_send.basic_broadcast(self.device_info_static.LAN_BROADCAST_IP,
                                               self.device_info_static.LAN_BROADCAST_PORT,
                                               message_formatter.require_message(self.device_info_static,
                                                                                 self.device_info_dynamic.PEER_vector_clock))
                        continue
                    # remove it from hold back queue
                    self.hold_back_queue.remove(entry)

                    self.device_info_dynamic.increase_vector_clock_entry(original_sender_id, 1)
                    self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
                    # store message that it can be resent if other peer lost it
                    self.delivered_queue.put(entry)
                    # co-deliver message
                    deliver_list.append((filename, temp_filename, message_type))
                # ordered multicast delivery
                for entry in deliver_list:
                    self.o_deliver_queue.put(entry)
            except KeyboardInterrupt:
                self.isRunning = False
            except Exception:
                continue

    def vector_clock_condition(self, sender_vector_clock: dict, sender_ID: int):
        self.update_device_info_dynamic()
        my_vector_clock = self.device_info_dynamic.PEER_vector_clock
        print(
            f"---clock---sender_ID:{sender_ID}---current:{self.device_info_dynamic.PEER_vector_clock}"
            f"---message:{sender_vector_clock}")
        if util.get_or_default(sender_vector_clock, sender_ID) != util.get_or_default(my_vector_clock, sender_ID) + 1:
            return False
        for peer in self.device_info_dynamic.PEERS:
            if peer == sender_ID:
                continue
            if util.get_or_default(sender_vector_clock, peer) > util.get_or_default(my_vector_clock, peer):
                return False
        return True



    def update_device_info_dynamic(self):
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
