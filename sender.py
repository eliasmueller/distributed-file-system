import platform
import socket

import deviceInfo
import file_transfer


broadcast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broadcast_socket_sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

buffer_size = 1024


def basic_broadcast(ip, port, message: str):
    # Send message on broadcast address
    broadcast_socket_sender.sendto(str.encode(message), (ip, port))
    # print(f"broadcasted {ip}, {port}: {message}")


def listen_for_broadcast_answer(timeout_seconds: int) -> str:
    broadcast_socket_sender.settimeout(timeout_seconds)
    while True:
        try:
            data, addr = broadcast_socket_sender.recvfrom(buffer_size)
        except socket.timeout:
            return None
        if data:
            return data.decode()

def basic_multicast(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, message_type, file_name: str):
    for p in device_info_dynamic.PEERS:
                    if p != device_info_static.PEER_ID:
                        ip = device_info_dynamic.PEER_IP_DICT[p]
                        file_transfer.transfer_file(ip=ip, port=7771, device_info_static=device_info_static, message_type=message_type, vector_clock=device_info_dynamic.PEER_vector_clock,
                                                    filename=file_name)

#def reliable_multicast(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, file_name: str):

