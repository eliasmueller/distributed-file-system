import socket
import ipaddress

import userIO

class DeviceInfoStatic():
    def __init__(self, my_peer_ID: int):
        #self aplication
        self.MY_STORAGE = ""
        self.PEER_ID = my_peer_ID

        #networking
        self.MY_HOST = socket.gethostname()
        self.MY_IP = socket.gethostbyname(self.MY_HOST)
        self.LAN_BOADCAST_IP = get_broadcast_IP(self.MY_IP,24)
        self.LAN_BROADCAST_PORT = 5971

    def print_info(self):
        print("Some general information:")
        print(f"ID: {self.PEER_ID}")
        print(f"Directory: {self.MY_STORAGE}\n")
        print(f"Host Name: {self.MY_HOST}, Host IP: {self.MY_IP}")
        print(f"Broadcast IP: {self.LAN_BOADCAST_IP}, Broadcast Port: {self.LAN_BROADCAST_PORT}\n")

class DeviceInfoDynamic():
    def __init__(self, my_peer_ID: int):
        #global view
        self.PEERS = [my_peer_ID]
        self.GROUPS = []
        self.IS_LEADER_IN_one_GROUP = False

    def print_info(self):
        print("Some dynamic information:")
        print(f"known peers: {self.PEERS}")
        print(f"known groups: {self.GROUPS}\n")

    def update_peer_view(self, new_peer_view):
        self.PEERS = new_peer_view



def get_network_IP(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.network_address)
    return network_ip

def get_broadcast_IP(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.broadcast_address)
    return network_ip


def lear_about_myself():
    my_peer_ID = userIO.ask_for_unique_ID()
    device_info_static = DeviceInfoStatic(my_peer_ID)
    device_info_dynamic = DeviceInfoDynamic(my_peer_ID)
    device_info_static.print_info()
    device_info_dynamic.print_info()
    return device_info_static, device_info_dynamic
