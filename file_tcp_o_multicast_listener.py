import socket
import multiprocessing
from functools import cmp_to_key

import file_transfer
import deviceInfo as deviceInfo
import util

buffer_size = 4096


class OrderedMulticastListener(multiprocessing.Process):
    def __init__(self,
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 receive_queue: multiprocessing.Queue,
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy,
                 lock):
        super(OrderedMulticastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.r_deliver_queue = receive_queue
        self.o_deliver_queue = deliver_queue
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
                #recieve reliable multicast delivery
                message = self.r_deliver_queue.get()
                #add to holdback
                self.hold_back_queue.append(message)

                #TODO sort hold back queue
                self.hold_back_queue = sorted(self.hold_back_queue, key=cmp_to_key(self.compare_vector_clocks))
                for entry in self.hold_back_queue.copy():#check if we actually can deliver the message or if we need to hold the changes back in the queue a bit longer
                    filename, vector_clock, temp_filename, sender_ID, message_type, original_sender_id = entry
                    #holdback check
                    if not self.vector_clock_condition(vector_clock, original_sender_id):
                        print("Holding back message in hold back queue")
                        continue
                    #remove it from hold back queue
                    self.hold_back_queue.remove(entry)

                    self.device_info_dynamic.increase_vector_clock_entry(original_sender_id, 1)
                    self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
                    #co-deliver message
                    #ordered multicast delivery
                    self.o_deliver_queue.put(filename, temp_filename, message_type)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def vector_clock_condition(self, sender_vector_clock: dict, sender_ID: int):
        self.update_device_info_dynamic()
        my_vector_clock = self.device_info_dynamic.PEER_vector_clock
        print(f"---clock---sender_ID:{sender_ID}---curent:{self.device_info_dynamic.PEER_vector_clock}---message:{sender_vector_clock}")
        if util.get_or_default(sender_vector_clock, sender_ID) != util.get_or_default(my_vector_clock, sender_ID) + 1:
            return False
        for peer in self.device_info_dynamic.PEERS:
            if peer == sender_ID:
                continue
            if util.get_or_default(sender_vector_clock, peer) > util.get_or_default(my_vector_clock, peer):
                return False
        return True

    def compare_vector_clocks(self, left_message, right_message):
        l_filename, l_vector_clock, l_temp_filename, l_sender_ID, l_message_type, l_original_sender_id = left_message
        r_filename, r_vector_clock, r_temp_filename, r_sender_ID, r_message_type, r_original_sender_id = right_message

        difference = 0
        for key, value in l_vector_clock.items():
            difference = difference + util.get_or_default(r_vector_clock, key) - value

        if difference < 0:
            return -1
        elif difference > 0:
            return 1
        else:
            return -1
        #return difference / abs(difference)

                
    def update_device_info_dynamic(self):
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
