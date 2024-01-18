import socket
import ipaddress



class DeviceInfoStatic:
    def __init__(self, my_peer_ID: int, my_storage: str):
        # self application
        self.MY_STORAGE = my_storage
        self.PEER_ID = my_peer_ID

        # networking
        self.MY_HOST = socket.gethostname()
        self.MY_IP = socket.gethostbyname(self.MY_HOST)
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

    def print_info(self):
        print("Some dynamic information:")
        print(f"known peers: {self.PEERS}")
        print(f"known groups: {self.GROUPS}\n")
        print(f"leader: {self.LEADER_ID}\n")

    def update_peer_view(self, new_peer_view: dict):
        self.PEERS = [*new_peer_view]
        self.PEER_IP_DICT = new_peer_view

    def append_new_peer(self, new_peer_id: int, new_peer_ip: str):
        self.PEERS.append(new_peer_id)
        self.PEER_IP_DICT[new_peer_id] = new_peer_ip


def get_network_ip(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.network_address)
    return network_ip


def get_broadcast_ip(device_ip, mask):
    network = ipaddress.IPv4Network(f"{device_ip}/{mask}", strict=False)
    network_ip = str(network.broadcast_address)
    return network_ip


def learn_about_myself():
    my_peer_id = 456  # uuid.uuid1().int
    my_storage = "/Users/p371728/sync-test"  # userIO.ask_for_folder_path_to_synchronise()
    device_info_static = DeviceInfoStatic(my_peer_id, my_storage)
    device_info_dynamic = DeviceInfoDynamic(my_peer_id, device_info_static.MY_IP)
    device_info_static.print_info()
    device_info_dynamic.print_info()
    return device_info_static, device_info_dynamic
