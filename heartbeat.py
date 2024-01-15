import multiprocessing
from multiprocessing.managers import DictProxy
import time
import threading
import deviceInfo
import sender as bSend

class heartbeat:
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic, shared_dict: DictProxy, interval = 5):
        self.device_info_static = device_info_static
        self.shared_dict = shared_dict
        self.interval = interval
        self.leader_ip = None
        self.leader_port = 17432
        self.run()

    def run(self):
        while True:
            if self.device_info_static.MY_IP == self.leader_ip:
                break
            self.get_device_info_update()
            if self.leader_ip is not None:
                self.send_heartbeat_to_leader()
            time.sleep(self.interval)

    def get_device_info_update(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        leader_id = self.device_info_dynamic.LEADER_ID
        if leader_id is not None:
            self.leader_ip = self.device_info_dynamic.PEER_IP_DICT[leader_id]

    def send_heartbeat_to_leader(self):
            bSend.send_unicast(ip=self.leader_ip, port=self.leader_port, message="heartbeat, something, senderIP: 192.168.178.70, senderID: something, hello there")
            print(f"Heartbeat sent to peer")
            response = bSend.listen_to_unicast(timeout_seconds=3)
            if response == None:
                 print("Heartbeat timed out")
            else:
                print(response)
