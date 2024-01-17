import multiprocessing
from multiprocessing.managers import DictProxy
import time
import threading
import deviceInfo
import sender as bSend
import socket

class heartbeat:
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic, shared_dict: DictProxy, interval = 5):
        self.device_info_static = device_info_static
        self.shared_dict = shared_dict
        self.interval = interval
        self.leader_ip = None
        self.heartbeat_port = 42044
        self.unicast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.unicast_socket_sender.bind((socket.gethostbyname(socket.gethostname()), 42044))
        self.buffer_size = 1024
        self.run()

    def run(self):
        while True:
            time.sleep(self.interval)
            self.get_device_info_update()

            if self.leader_ip is None:
                continue
            elif self.device_info_static.MY_IP == self.leader_ip:
                self.leader_receive_and_reply()

            self.send_heartbeat_to_leader()
            response = self.wait_for_response(timeout_seconds=3)
            if response == None:
                print("Heartbeat timed out")
                # TODO Restart Bully Algorithm
            else:
                sender_ip = self.extract_sender_ip(response)
                if sender_ip != self.leader_ip:
                    raise Exception("Received heartbeat response from non leader. This is not allowed") 

    def get_device_info_update(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        leader_id = self.device_info_dynamic.LEADER_ID
        if leader_id is not None:
            self.leader_ip = self.device_info_dynamic.PEER_IP_DICT[leader_id]

    def send_heartbeat_to_leader(self):
        self.unicast_socket_sender.sendto(str.encode(f"heartbeat,{self.device_info_static.MY_IP}"), (self.leader_ip, self.heartbeat_port))
        print(f"Heartbeat sent to leader")

    def leader_receive_and_reply(self):
        while True:
            response = self.wait_for_response(timeout_seconds=100)
            if response == None:
                print("Heartbeat timed out")
            else:
                # TODO: send back message to sender to acknowledge
                 sender_ip = self.extract_sender_ip(response)
                 self.unicast_socket_sender.sendto(str.encode(f"heartbeat,{self.device_info_static.MY_IP}"), (sender_ip, self.heartbeat_port))

    def extract_sender_ip(self, message):
        message_split = message.split(',')
        sender_ip = message_split[1]
        return sender_ip

    # def send_unicast(self, ip, port, message: str):
    #     print("sending udp to ip:", ip, "port:", port)
    #     self.unicast_socket_sender.sendto(str.encode(message), (ip, port))

    def wait_for_response(self, timeout_seconds: int):
        self.unicast_socket_sender.settimeout(timeout_seconds)
        while True:
            try:
                data, addr = self.unicast_socket_sender.recvfrom(self.buffer_size)
            except socket.timeout:
                return None
            if data:
                return data.decode()