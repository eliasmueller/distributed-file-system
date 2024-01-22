import socket
import multiprocessing
import os

import file_transfer
import deviceInfo as deviceInfo
import util

buffer_size = 4096


class ReliableMulticastListener(multiprocessing.Process):
    def __init__(self, 
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy):
        super(ReliableMulticastListener, self).__init__()
        self.device_info_static = device_info_static
        self.r_deliver_queue = deliver_queue
        self.shared_dict = shared_dict
        self.port = 7771
        # Create a TCP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.device_info_static.MY_IP, self.port))
        self.buffer_size = buffer_size
        self.isRunning = True

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
            # TODO proper exception handling
            except Exception:
                continue

    def r_listen(self, message):
        #TODO check for duplicates
        #TODO add to recieved messanges
        #TODO if sender_id == my_id b-multicast
        #reliable multicast deliver
        if not self.r_deliver_queue.full():
            self.r_deliver_queue.put(message)
        else:
            print("Exception--------------------------------------------------------------")#TODO remove print
            raise Exception


