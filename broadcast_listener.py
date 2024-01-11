import socket
import multiprocessing

import messageFormater as formater
import deviceInfo as deviceInfo

buffer_size = 1024
static_broadcast_ip = "0.0.0.0"


class BroadcastListener(multiprocessing.Process):
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue, shared_dict: multiprocessing.managers.DictProxy):
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
        # TODO check why the device's IP is not working and the static broadcast IP has to be used for broadcasting
        self.listen_socket.bind((static_broadcast_ip, self.device_info_static.LAN_BROADCAST_PORT))
#        self.listen_socket.bind((self.device_info_static.MY_IP, self.device_info_static.LAN_BROADCAST_PORT))
        self.buffer_size = buffer_size
        self.isRunning = True
    
    def run(self):
        print("Listening to broadcast messages")
        try:
            self.listen(self.device_info_static, self.device_info_dynamic)
        finally:
            self.listen_socket.close()

    def listen(self, device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic):
        # recvfrom is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                data, addr = self.listen_socket.recvfrom(self.buffer_size)
                if data:
                    print(f"Received broadcast from {addr} with the message: {data.decode()}")
                    answer = formater.process_message(device_info_static, device_info_dynamic, data.decode(), self.shared_queue)
                    if answer:
                        self.answer(addr, answer)
            except KeyboardInterrupt:
                # TODO dose not work yet
                self.isRunning = False

    def answer(self, sender_address, message: str):
        self.listen_socket.sendto(str.encode(message), sender_address)


