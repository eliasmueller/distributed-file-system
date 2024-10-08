import socket
import time
from datetime import datetime
from multiprocessing.managers import DictProxy
from typing import List

import device_info
import message_formatter
import message_formatter as formatter
import sender as b_send
import shared_dict_helper
from shared_dict_helper import DictKey


class Heartbeat:
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 shared_dict: DictProxy,
                 lock,
                 interval=5):
        self.device_info_static = device_info_static
        self.shared_dict = shared_dict
        self.interval = interval
        self.leader_id = None
        self.leader_ip = None
        self.peer_ip_dict = dict()
        self.heartbeat_port = 42044
        self.unicast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.unicast_socket_sender.bind((device_info_static.MY_IP, 42044))
        self.buffer_size = 1024
        self.lock = lock
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
                    sender_ip = formatter.get_sender_ip(response)
                    if sender_ip != self.leader_ip:
                        print("Received heartbeat response from non leader. This should not be happening")
                        continue

    def reset_leader_information(self):
        self.leader_ip = None
        self.leader_id = None
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.leader_id, self.leader_id)

    def get_device_info_update(self):
        self.peer_ip_dict = self.shared_dict[DictKey.peer_ip_dict.value]
        self.leader_id = self.shared_dict[DictKey.leader_id.value]
        if self.leader_id is not None:
                self.leader_ip = self.peer_ip_dict[self.leader_id]
        else:
            self.leader_ip = None

    def send_heartbeat_to_leader(self):
        try:
            self.unicast_socket_sender.sendto(str.encode(formatter.request_heartbeat_message(self.device_info_static)),
                                          (self.leader_ip, self.heartbeat_port))
            print(f"Heartbeat sent to leader")
        except Exception:
            pass

    def leader_receive_and_reply(self):
        heartbeat_timestamps = {value: datetime.now() for value in self.peer_ip_dict.values()}
        heartbeat_timestamps.pop(self.device_info_static.MY_IP)
        while True:
            self.get_device_info_update()
            if self.leader_id != self.device_info_static.PEER_ID:
                print("Stopping working as a leader")
                break

            # manage and update dynamic peer view, and broadcast current cluster state
            current_time = datetime.now()
            dead_peer_ips = [key for key, timestamp in heartbeat_timestamps.items() if
                             (current_time - timestamp).total_seconds() > 12.0]
            if dead_peer_ips:
                for ip in dead_peer_ips:
                    del heartbeat_timestamps[ip]
                self.remove_dead_peers(dead_peer_ips)

            response = self.wait_for_response(timeout_seconds=3)
            if response is None:
                continue
            else:
                sender_ip = formatter.get_sender_ip(response)
                print(f"Received heartbeat message from {sender_ip}. Sending Response...")
                self.unicast_socket_sender.sendto(
                    str.encode(formatter.response_heartbeat_message(self.device_info_static)),
                    (sender_ip, self.heartbeat_port))
                heartbeat_timestamps[sender_ip] = datetime.now()

    def wait_for_response(self, timeout_seconds: int):
        self.unicast_socket_sender.settimeout(timeout_seconds)
        while True:
            try:
                data, addr = self.unicast_socket_sender.recvfrom(self.buffer_size)
            except socket.timeout:
                return None
            except ConnectionResetError:
                return None
            if data:
                return data.decode()

    def remove_dead_peers(self, dead_peer_ips: List[str]):
        dead_ids = []
        vector_clock = self.shared_dict[DictKey.peer_vector_clock.value]
        peers = self.shared_dict[DictKey.peers.value]
        for ip in dead_peer_ips:
            for key, value in self.peer_ip_dict.items():
                if value == ip:
                    dead_ids.append(key)
        for dead_id in dead_ids:
            peers.remove(dead_id)
            del self.peer_ip_dict[dead_id]
            if dead_id in vector_clock.keys():
                del vector_clock[dead_id]
            print(f"Removing dead peer {dead_id} from group.")
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_ip_dict, self.peer_ip_dict)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peers, peers)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_vector_clock, vector_clock)

        message = message_formatter.remove_peer_view(self.device_info_static, dead_ids)

        b_send.basic_broadcast(self.device_info_static.LAN_BROADCAST_IP,
                               self.device_info_static.LAN_BROADCAST_PORT, str(message))
