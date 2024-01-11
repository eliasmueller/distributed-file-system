import socket
import multiprocessing

import file_transfer
import deviceInfo as deviceInfo

buffer_size = 4096


class FileListener(multiprocessing.Process):
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
        super(FileListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.port = 7771
        # Create a TCP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.device_info_static.MY_IP, self.port))
        self.buffer_size = buffer_size
        self.isRunning = True

    def run(self):
        print("Listening to tcp connections on port 7771")
        try:
            self.listen(self.device_info_static, self.device_info_dynamic)
        finally:
            self.listen_socket.close()

    def listen(self, device_info_static: deviceInfo.DeviceInfoStatic,
               device_info_dynamic: deviceInfo.DeviceInfoDynamic):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.listen_socket.listen()
                conn_socket, addr = self.listen_socket.accept()
                if conn_socket:
                    print(f"Received tcp connection handshake from {addr}")
                    file_transfer.listen_for_file(conn_socket, self.device_info_static)
            except KeyboardInterrupt:
                self.isRunning = False
            except Exception:
                continue

    def answer(self, sender_address, message: str):
        self.listen_socket.sendto(str.encode(message), sender_address)


