import multiprocessing
import socket
from multiprocessing.managers import DictProxy

import device_info
import file_transfer
import message_formatter as formatter
import message_processor

BUFFER_SIZE = 1024
STATIC_BROADCAST_IP = "0.0.0.0"


class BroadcastListener(multiprocessing.Process):
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 device_info_dynamic: device_info.DeviceInfoDynamic,
                 shared_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        super(BroadcastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.shared_dict = shared_dict
        # Listening port
        # Create a UDP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the socket to broadcast and enable reusing addresses
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind socket to address and port
        self.listen_socket.bind((STATIC_BROADCAST_IP, self.device_info_static.LAN_BROADCAST_PORT))
        # self.listen_socket.bind((self.device_info_static.MY_IP, self.device_info_static.LAN_BROADCAST_PORT))
        self.buffer_size = BUFFER_SIZE
        self.lock = lock
        self.isRunning = True

    def run(self):
        print("Listening to broadcast messages")
        try:
            self.listen()
        finally:
            self.listen_socket.close()

    def listen(self):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
            try:
                data, addr = self.listen_socket.recvfrom(self.buffer_size)
                if data:
                    answer = message_processor.process_message(self.device_info_static,
                                                               self.device_info_dynamic,
                                                               data.decode(),
                                                               self.shared_queue,
                                                               self.shared_dict,
                                                               self.lock)
                    if answer:
                        self.answer(addr, answer)
                        if self.device_info_dynamic.LEADER_ID == self.device_info_static.PEER_ID:
                            # if this peer is the leader let the new one know already
                            self.answer(addr, formatter.get_election_message(self.device_info_static,
                                                                             "leader",
                                                                             "init-no-election-id"))
                            self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
                            file_transfer.transfer_entire_folder(self.device_info_static,
                                                                 self.device_info_dynamic,
                                                                 addr[0])
            except KeyboardInterrupt:
                self.isRunning = False

    def answer(self, sender_address, message: str):
        self.listen_socket.sendto(str.encode(message), sender_address)
