import socket
import multiprocessing
import os

import file_transfer
import deviceInfo as deviceInfo
import message_formater as formater
import sender as bSend
import util

buffer_size = 4096


class ReliableMulticastListener(multiprocessing.Process):
    def __init__(self, 
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy,
                 lock):
        super(ReliableMulticastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.r_deliver_queue = deliver_queue
        self.shared_dict = shared_dict
        self.lock = lock
        self.port = 7771
        # Create a TCP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.device_info_static.MY_IP, self.port))
        self.buffer_size = buffer_size
        self.isRunning = True
        self.recieved_messages = []
    def run(self):
        print(f"Listening to tcp connections on port {self.port}")
        try:
            self.b_listen()
        finally:
            self.listen_socket.close()

    def b_listen(self):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                #b-listen
                message = file_transfer.listen_for_file(self.listen_socket, self.device_info_static)
                #b-deliver to reliable listener
                self.r_listen(message)
            except KeyboardInterrupt:
                self.isRunning = False
            except Exception:
                continue

    def r_listen(self, message):
        filename, vector_clock, temp_filename, sender_id, message_type, original_sender_id = message
        if self.is_duplicate(message):
            util.delete_file(temp_filename, self.device_info_static.MY_STORAGE)
            print("duplicate")
            return
        self.recieved_messages.append(message)
        if self.device_info_static.PEER_ID != sender_id:
            #sender_id != my_id
            #b-multicast same message agean
            self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
            bSend.basic_multicast_for_reliable_resent(device_info_static=self.device_info_static, original_sender_id=sender_id, device_info_dynamic=self.device_info_dynamic, vector_clock=vector_clock, message_type=message_type, file_location_name=temp_filename, file_name=filename)
        #reliable multicast deliver
        self.r_deliver_queue.put(message)
        self.remove_old_recieved_messages()

    def is_duplicate(self, message) -> bool:
        #n_sender_id and n_temp_filename can be different even if it is considered a duplicate message.
        n_filename, n_vector_clock, n_temp_filename, n_sender_id, n_message_type, n_original_sender_id = message
        for r_filename, r_vector_clock, r_temp_filename, r_sender_id, r_message_type, r_original_sender_id in self.recieved_messages:
            if r_original_sender_id != n_original_sender_id:
                continue
            if r_filename != n_filename:
                continue
            if r_message_type.strip() != n_message_type.strip():
                continue
            if r_vector_clock == n_vector_clock:
                return True
        return False

    def remove_old_recieved_messages(self):
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        recieved_messages_copy = self.recieved_messages.copy()
        self.recieved_messages.clear()
        for entry in recieved_messages_copy:
            n_filename, n_vector_clock, n_temp_filename, n_sender_id, n_message_type, n_original_sender_id = entry
            for clock_key, clock_value in self.device_info_dynamic.PEER_vector_clock.items():
                if util.get_or_default(n_vector_clock, clock_key) >= clock_value - 5:
                    self.recieved_messages.append(entry)
                    break



