import socket
import multiprocessing

import messageFormater as formater

buffer_size = 1024

class BroadcastListener(multiprocessing.Process):
    def __init__(self, device_info_static, device_info_dynamic, shared_queue):
        super(BroadcastListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        # Listening port
        # Create a UDP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the socket to broadcast and enable reusing addresses
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind socket to address and port
        self.listen_socket.bind((self.device_info_static.MY_IP, self.device_info_static.LAN_BROADCAST_PORT))
        self.buffer_size = buffer_size
        self.isRunning = True
    
    def run(self):
        print("Listening to broadcast messages")
        try:
            self.listen(self.device_info_static, self.device_info_dynamic)
        finally:
            self.listen_socket.close()

    def listen(self, device_info_static, device_info_dynamic):
        #recvfrom is waiting until it recieves something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                data, addr = self.listen_socket.recvfrom(self.buffer_size)
                if data:
                    print(f"Received broadcast from {addr} with the message: {data.decode()}")
                    answer = formater.process_message(device_info_static, device_info_dynamic, data.decode())
                    if answer:
                        self.answer(addr, answer)
            except KeyboardInterrupt:
                #TODO dose not work jet
                self.isRunning = False

    def answer(self, sender_address, message):
        self.listen_socket.sendto(str.encode(message), sender_address)


