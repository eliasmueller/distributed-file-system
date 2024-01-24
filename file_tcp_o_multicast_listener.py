import socket
import multiprocessing
import os

import file_transfer
import deviceInfo as deviceInfo
import util

buffer_size = 4096


class OrderedMulticastListener(multiprocessing.Process):
    def __init__(self, 
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic, 
                 recieve_queue: multiprocessing.Queue,
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy):
        super(OrderedMulticastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.r_deliver_queue = recieve_queue
        self.o_deliver_queue = deliver_queue
        self.shared_dict = shared_dict
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
                message =  self.check_hold_back_queue()
                #ordered multicast delivery
                self.o_deliver_queue.put(message)
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

    def check_hold_back_queue(self) -> (str, str, str):
        #check if we actually can deliver the message or if we need to hold the changes back in the queue a bit longer
        filename, vector_clock, temp_filename, sender_ID, message_type, original_sender_id = self.hold_back_queue[0]
        
        #holdback check
        while not self.vector_clock_condition(vector_clock, original_sender_id):
            print("Holding back message in hold back queue")
            # TODO do we nead to rotate the queue entrys to afoid deadlocks and starvation ?
            # TODO add message to hold back queue and ensure other messages are incoming first
        #remove it from hold back queue
        filename, vector_clock, temp_filename, sender_ID, message_type, original_sender_id = self.hold_back_queue.pop()
        #TODO in parallel execution self.hold_back_queue[0] != self.hold_back_queue.pop() possible
        self.device_info_dynamic.increase_vector_clock_entry(original_sender_id, 1)
        self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)
        #co-deliver message
        return filename, temp_filename, message_type
                
    def update_device_info_dynamic(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")