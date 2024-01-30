import socket

import device_info
import file_transfer

BROADCAST_SOCKET_SENDER = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
BROADCAST_SOCKET_SENDER.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

BUFFER_SIZE = 1024


def basic_broadcast(ip, port, message: str):
    # Send message on broadcast address
    BROADCAST_SOCKET_SENDER.sendto(str.encode(message), (ip, port))


def listen_for_broadcast_answer(timeout_seconds: int) -> str | None:
    BROADCAST_SOCKET_SENDER.settimeout(timeout_seconds)
    while True:
        try:
            data, addr = BROADCAST_SOCKET_SENDER.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            return None
        if data:
            return data.decode()


def basic_multicast(device_info_static: device_info.DeviceInfoStatic,
                    device_info_dynamic: device_info.DeviceInfoDynamic,
                    message_type,
                    file_name: str):
    for p in device_info_dynamic.PEERS:
        if p != device_info_static.PEER_ID:
            ip = device_info_dynamic.PEER_IP_DICT[p]
            file_transfer.transfer_file(ip=ip, port=7771, original_sender_id=device_info_static.PEER_ID,
                                        device_info_static=device_info_static,
                                        message_type="file transfer " + message_type,
                                        vector_clock=device_info_dynamic.PEER_vector_clock,
                                        file_location_name=file_name, filename=file_name)


def basic_multicast_for_reliable_resent(device_info_static: device_info.DeviceInfoStatic, original_sender_id: int,
                                        device_info_dynamic: device_info.DeviceInfoDynamic, vector_clock: dict,
                                        message_type, file_location_name: str, file_name: str):
    for p in device_info_dynamic.PEERS:
        if p == device_info_static.PEER_ID:
            continue
        if p == original_sender_id:
            continue
        ip = device_info_dynamic.PEER_IP_DICT[p]
        file_transfer.transfer_file(ip=ip, port=7771, original_sender_id=original_sender_id,
                                    device_info_static=device_info_static, message_type=message_type,
                                    vector_clock=vector_clock, file_location_name=file_location_name,
                                    filename=file_name)


def reliable_multicast(device_info_static: device_info.DeviceInfoStatic,
                       device_info_dynamic: device_info.DeviceInfoDynamic, message_type, file_name: str):
    basic_multicast(device_info_static, device_info_dynamic, message_type, file_name)
    # The sending of reliable multicast is the same.
    # Just adding this to keep sending and receiving levels consistent.
