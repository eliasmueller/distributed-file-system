import socket
import ipaddress
import uuid
import os

import userIO
import util

def get_my_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    my_ip = s.getsockname()[0]
    s.close()
    return my_ip

class DeviceInfoStatic:
    def __init__(self, my_peer_ID: int, my_storage: str):
        # self application
        self.MY_STORAGE = my_storage
        self.PEER_ID = my_peer_ID

        # networking
        self.MY_HOST = socket.gethostname()
        self.MY_IP = get_my_ip()
        self.LAN_BROADCAST_IP = get_broadcast_ip(self.MY_IP, 24)
        self.LAN_BROADCAST_PORT = 5971

    def print_info(self):
        print("Some general information:")
        print(f"ID: {self.PEER_ID}")
        print(f"Directory: {self.MY_STORAGE}\n")
        print(f"Host Name: {self.MY_HOST}, Host IP: {self.MY_IP}")
        print(f"Broadcast IP: {self.LAN_BROADCAST_IP}, Broadcast Port: {self.LAN_BROADCAST_PORT}\n")


class DeviceInfoDynamic:
    def __init__(self, my_peer_ID: int, my_peer_IP):
        # global view
        self.PEERS = [my_peer_ID]
        self.PEER_IP_DICT = {my_peer_ID: my_peer_IP}
        self.GROUPS = []
        self.IS_LEADER_IN_ONE_GROUP = False
        self.LEADER_ID: int | None = None
        self.PEER_file_state = {}
        self.PEER_vector_clock = dict() # TODO clean peer entries of ofline peers on heartbeat

    def print_info(self):
        print("Some dynamic information:")
        print(f"known peers: {self.PEERS}")
        print(f"known groups: {self.GROUPS}\n")
        print(f"leader: {self.LEADER_ID}\n")
        print(f"vector clock: {self.PEER_vector_clock}\n")

    def update_peer_view(self, new_peer_view: dict):
        self.PEERS = [*new_peer_view]
        self.PEER_IP_DICT = new_peer_view

    def update_vector_clock(self, extern_vector_clock: dict):
        for key, value in extern_vector_clock.items():
            peer_clock_val = util.get_or_default(self.PEER_vector_clock, key)
            if value < peer_clock_val:
                raise Exception #an unconected peer schould not have vector clocks that are furthere along then network peers
            self.PEER_vector_clock.update({key : max(0, peer_clock_val, value)})

    def increase_vector_clock_entry(self, peer, increment_size: int):
        peer_clock_val = util.get_or_default(self.PEER_vector_clock, peer)
        self.PEER_vector_clock.update({peer : max(0, peer_clock_val, peer_clock_val + increment_size)})

    def append_new_peer(self, new_peer_id: int, new_peer_ip: str):
        self.PEERS.append(new_peer_id)
        self.PEER_IP_DICT[new_peer_id] = new_peer_ip

def get_host_ip(host_name):
    #self.MY_IP = socket.gethostbyname(host_name)
    #TODO if the peer has more than one ip address find the right one
    ip = socket.gethostbyname_ex(host_name)
    print(ip)
    return ip[2][len(ip[2])-1]

def get_network_ip(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.network_address)
    return network_ip

def get_broadcast_ip(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.broadcast_address)
    return network_ip

def initialise_myself(uuid_of_peer:int = uuid.uuid1().int, path: str = ""):
    my_peer_id = uuid_of_peer
    my_storage = path
    if path == "":
        my_storage = userIO.ask_for_folder_path_to_synchronise()
    device_info_static = DeviceInfoStatic(my_peer_id, my_storage)
    device_info_dynamic = DeviceInfoDynamic(my_peer_id, device_info_static.MY_IP)
    device_info_static.print_info()
    device_info_dynamic.print_info()
    return device_info_static, device_info_dynamic
