from multiprocessing.managers import DictProxy
import time
import deviceInfo
import socket


class Heartbeat:
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic, shared_dict: DictProxy, interval=5):
        self.device_info_static = device_info_static
        self.shared_dict = shared_dict
        self.interval = interval
        self.leader_ip = None
        self.heartbeat_port = 42044
        self.unicast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.gethostbyname_ex(socket.gethostname())
        self.unicast_socket_sender.bind((ip[2][len(ip[2])-1], 42044))
        self.buffer_size = 1024
        self.run()

    def run(self):
        heartbeat_timeout_counter = 0
        while True:
            time.sleep(self.interval)
            self.get_device_info_update()

            if self.leader_ip is None:
                continue
            elif self.device_info_static.MY_IP == self.leader_ip:
                self.leader_receive_and_reply()
            else:
                self.send_heartbeat_to_leader()
                response = self.wait_for_response(timeout_seconds=3)
                if response is None:
                    print("Heartbeat timed out")
                    heartbeat_timeout_counter += 1
                    if heartbeat_timeout_counter >= 2:
                        print("Second timeout of heartbeat, starting new election.")
                        heartbeat_timeout_counter = 0
                        self.reset_leader_information()

                else:
                    print("Heartbeat answer received")
                    sender_ip = extract_sender_ip(response)
                    if sender_ip != self.leader_ip:
                        raise Exception("Received heartbeat response from non leader. This is not allowed")

    def reset_leader_information(self):
        self.leader_ip = None
        self.device_info_dynamic.LEADER_ID = None
        self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)

    def get_device_info_update(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        leader_id = self.device_info_dynamic.LEADER_ID
        if leader_id is not None:
            self.leader_ip = self.device_info_dynamic.PEER_IP_DICT[leader_id]
        else:
            self.leader_ip = None

    def send_heartbeat_to_leader(self):
        self.unicast_socket_sender.sendto(str.encode(f"heartbeat,{self.device_info_static.MY_IP}"),
                                          (self.leader_ip, self.heartbeat_port))
        print(f"Heartbeat sent to leader")

    def leader_receive_and_reply(self):
        while True:
            self.get_device_info_update()
            if self.device_info_dynamic.LEADER_ID != self.device_info_static.PEER_ID:
                print("Stopping working as a leader")
                break

            response = self.wait_for_response(timeout_seconds=3)
            if response is None:
                continue
            else:
                sender_ip = extract_sender_ip(response)
                print(f"Received heartbeat message from {sender_ip}. Sending Response...")
                self.unicast_socket_sender.sendto(str.encode(f"heartbeat,{self.device_info_static.MY_IP}"),
                                                  (sender_ip, self.heartbeat_port))

    def wait_for_response(self, timeout_seconds: int):
        self.unicast_socket_sender.settimeout(timeout_seconds)
        while True:
            try:
                data, addr = self.unicast_socket_sender.recvfrom(self.buffer_size)
            except socket.timeout:
                return None
            if data:
                return data.decode()


def extract_sender_ip(message):
    message_split = message.split(',')
    sender_ip = message_split[1]
    return sender_ip
