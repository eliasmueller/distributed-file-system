import socket
import multiprocessing
from multiprocessing.managers import DictProxy
import os
import time

import file_transfer
import deviceInfo as deviceInfo
from shared_dict_helper import DictKey
import shared_dict_helper
import util

buffer_size = 4096


class FileListener(multiprocessing.Process):
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 shared_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        super(FileListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.shared_dict = shared_dict
        self.port = 7771
        # Create a TCP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.device_info_static.MY_IP, self.port))
        self.buffer_size = buffer_size
        self.isRunning = True
        self.hold_back_queue = []
        self.lock = lock
        self.hold_back_locked_files = []

    def run(self):
        print("Listening to tcp connections on port 7771")
        try:
            self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
            self.listen()
        finally:
            self.listen_socket.close()

    def listen(self):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                if self.hold_back_locked_files:
                    for (file_name, temp_filename, message_type) in self.hold_back_locked_files:
                        if not self.check_locked_file(file_name):
                            self.update_file_from_tempfile(file_name, temp_filename, message_type)

                file_name, temp_filename, message_type = self.consistent_order_listen()

                if temp_filename:
                    if self.check_locked_file(file_name):
                        self.hold_back_locked_files.append((file_name, temp_filename, message_type))
                        print(f"Not applying received file changes because file is locked locally.")
                    else:
                        print(f"Received file changes")
                        self.update_file_from_tempfile(file_name, temp_filename, message_type)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def update_file_from_tempfile(self, filename: str, temp_filename: str, message_type: str):
        #override file
        filepath_file = f"{self.device_info_static.MY_STORAGE}/{filename}"
        filepath_temp = f"{self.device_info_static.MY_STORAGE}/{temp_filename}"
        if message_type == " file transfer delete":
            if os.path.exists(filepath_file):
                os.remove(filepath_file)
            if os.path.exists(filepath_temp):
                os.remove(filepath_temp)
        else:
            os.replace(filepath_temp, filepath_file)

        #update monitor last file change view
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state, util.get_folder_state(self.device_info_static.MY_STORAGE))

    def vector_clock_condition(self, sender_vector_clock: dict, sender_ID: int, filename: str):
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        my_vector_clock = self.device_info_dynamic.PEER_vector_clock
        print(f"------clock-------curent:{self.device_info_dynamic.PEER_vector_clock}")
        print(f"------clock-------message:{sender_vector_clock}")
        if util.get_or_default(sender_vector_clock, sender_ID) != util.get_or_default(my_vector_clock, sender_ID) + 1:
            return False
        for peer in self.device_info_dynamic.PEERS:
            if peer == sender_ID:
                continue
            if util.get_or_default(sender_vector_clock, peer) > util.get_or_default(my_vector_clock, peer):
                return False
        return True

    def check_locked_file(self, filename) -> bool:
        # If a file is locked we keep everything in the hold back queue until unlocked again to ensure consistency and mark the file as remote edited
        if filename in self.device_info_dynamic.LOCKED_FILES.keys():
            print(f"Received change for locked file {filename}, holding it back in the queue.")
            self.device_info_dynamic.LOCKED_FILES[filename] = "remote"
            self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
            return True
        else:
            return False

    def consistent_order_listen(self) -> (str, str, str):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        #add to holdback
        self.hold_back_queue.append(self.b_listen())
        # TODO instead of (iterating over peers tcp) B multicast use (tcp) R multicast
        return self.check_hold_back_queue()

    def check_hold_back_queue(self) -> (str, str, str):
        #check if we actually can deliver the message or if we need to hold the changes back in the queue a bit longer
        filename, vector_clock, temp_filename, sender_ID, message_type = self.hold_back_queue[0]
        #holdback check
        while not self.vector_clock_condition(vector_clock, sender_ID, filename):
            print("Holding back message in hold back queue")
            time.sleep(1)
            # TODO do we nead to rotate the queue entrys to afoid deadlocks and starvation ?
            # TODO add message to hold back queue and ensure other messages are incoming first
        #remove it from hold back queue
        filename, vector_clock, temp_filename, sender_ID, message_type = self.hold_back_queue.pop()
        #TODO in parallel execution self.hold_back_queue[0] != self.hold_back_queue.pop() possible

        self.device_info_dynamic.increase_vector_clock_entry(sender_ID, 1)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_vector_clock, self.device_info_dynamic.PEER_vector_clock)
        #co-deliver message
        return filename, temp_filename, message_type

    def b_listen(self) -> (str, dict, str, int, str):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:    
                return file_transfer.listen_for_file(self.listen_socket, self.device_info_static)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def answer(self, sender_address, message: str):
        self.listen_socket.sendto(str.encode(message), sender_address)
