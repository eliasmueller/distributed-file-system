import socket
import multiprocessing
import os

import file_transfer
import deviceInfo as deviceInfo
import util

buffer_size = 4096


class FileListener(multiprocessing.Process):
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy):
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

    def run(self):
        print("Listening to tcp connections on port 7771")
        try:
            self.update_device_info_dynamic()
            self.listen()
        finally:
            self.listen_socket.close()

    def listen(self):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                file_name, temp_filename = self.consistent_order_listen()
                if temp_filename:
                    print(f"Received file changes")
                    # TODO what to do with changes now we can update the local file from the ordered reliable multicast
                    self.update_file_from_tempfile(file_name, temp_filename)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def update_file_from_tempfile(self, filename: str, temp_filename: str):
        #override file
        print("updated file--------------------------------------------")
        filepath_file = f"{self.device_info_static.MY_STORAGE}/{filename}"
        filepath_temp = f"{self.device_info_static.MY_STORAGE}/{temp_filename}"
        os.replace(filepath_temp, filepath_file)
        #f.write(bytes_read)# TODO this is curently to early maybe in a temp file
        #update monitor last file change view
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        self.device_info_dynamic.PEER_file_state = {f: os.path.getmtime(os.path.join(self.device_info_static.MY_STORAGE, f)) for f in
                                                                os.listdir(self.device_info_static.MY_STORAGE)}
        #TODO use the funktion from monitor_local_folder
        self.shared_dict.update(device_info_dynamic = self.device_info_dynamic)

    def vector_clock_conditon(self, sender_vector_clock: dict, sender_ID: int):
        self.update_device_info_dynamic()
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

    def consistent_order_listen(self) -> (str, str):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        #add to holdback
        self.hold_back_queue.append(self.b_listen())
        # TODO instead of (iterating over peers tcp) B multicast use (tcp) R multicast
        return self.check_hold_back_queue()

    def check_hold_back_queue(self) -> (str,str):
        #check if we actually can deliver the message or if we need to hold the changes back in the queue a bit longer
        filename, vector_clock, temp_filename, sender_ID = self.hold_back_queue[0]
        #holdback check
        while not self.vector_clock_conditon(vector_clock, sender_ID):
            print("Holding back message in hold back queue")
            # TODO do we nead to rotate the queue entrys to afoid deadlocks and starvation ?
            # TODO add message to hold back queue and ensure other messages are incoming first
        #remove it from hold back queue
        filename, vector_clock, temp_filename, sender_ID = self.hold_back_queue.pop()
        #TODO in parallel execution self.hold_back_queue[0] != self.hold_back_queue.pop() possible
        self.device_info_dynamic.increase_vector_clock_entry(sender_ID, 1)
        self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)
        #co-deliver message
        return filename, temp_filename

    def b_listen(self) -> (str, dict, str):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.listen_socket.listen()
                conn_socket, addr = self.listen_socket.accept()
                if conn_socket:
                    print(f"Received tcp connection handshake from {addr}")
                    return file_transfer.listen_for_file(conn_socket, self.device_info_static)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def answer(self, sender_address, message: str):
        self.listen_socket.sendto(str.encode(message), sender_address)

                
    def update_device_info_dynamic(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
