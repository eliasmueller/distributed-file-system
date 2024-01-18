import socket
import multiprocessing

import file_transfer
import deviceInfo as deviceInfo

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

    def run(self):
        print("Listening to tcp connections on port 7771")
        try:
            self.listen()
        finally:
            self.listen_socket.close()

    def listen(self):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                file_name, file_changes = self.consistent_order_listen()
                if file_changes:
                    print(f"Received file changes")
                    # TODO what to do with changes
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def vector_clock_conditon(self, sender_vector_clock: dict, sender_ID: int):
        if sender_vector_clock.get(sender_ID) != self.device_info_dynamic.PEER_vector_clock.get(sender_ID) + 1:
            return False
        for peer in self.device_info_dynamic.PEERS:
            if peer == sender_ID:
                continue
            if sender_vector_clock.get(peer) > self.device_info_dynamic.PEER_vector_clock.get(peer):
                return False
        return True

    def consistent_order_listen(self) -> str:
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        # TODO instead of (iterating over peers tcp) B multicast use (tcp) R multicast
        filename, vector_clock, temp_filename, sender_ID = self.b_listen()

        #add to holdback

        # TODO here we must check if we actually can deliver the message or if we need to hold the changes back in the queue
        #holdback check
        while not self.vector_clock_conditon(vector_clock, sender_ID):
            print("Holding back message in hold back queue")
            break # for testing
            # TODO add message to hold back queue and ensure other messages are incoming first
        

        #remove it from hold back que
        self.device_info_dynamic.increase_vector_clock_entry(sender_ID, 1)
    
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
