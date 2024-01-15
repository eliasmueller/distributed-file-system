import multiprocessing
from multiprocessing.managers import DictProxy
import time
import threading
import deviceInfo
import sender as bSend

class heartbeat:
    def __init__(self, shared_dict: DictProxy, interval = 5):
        self.shared_dict = shared_dict
        self.interval = interval
        self.leader_ip = ""
        self.leader_port = 5971
        self.run()

    def run(self):
        while True:
            self.get_device_info_update()
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
            response = bSend.listen_to_unicast(3)
            if response == None:
                 print("Heartbeat timed out")
            else:
                print(response)
