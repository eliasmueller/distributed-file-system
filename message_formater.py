from typing import List
import deviceInfo as deviceInfo

def request_discovery(device_info_static: deviceInfo.DeviceInfoStatic,
                      device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'request, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}<SEPARATOR> senderVectorClock: {device_info_dynamic.PEER_vector_clock}'


def response_discovery(device_info_static: deviceInfo.DeviceInfoStatic,
                       device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'response, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}<SEPARATOR> senderVectorClock: {device_info_dynamic.PEER_vector_clock}'


def update_peer_view(device_info_static: deviceInfo.DeviceInfoStatic,
                     device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'update, peer view, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}<SEPARATOR> senderVectorClock: {device_info_dynamic.PEER_vector_clock}'


def remove_peer_view(device_info_static: deviceInfo.DeviceInfoStatic, peersToBeRemoved: List[int]) -> str:
    return f'remove, peer view, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, peersToBeRemoved: {peersToBeRemoved}'


def get_election_message(device_info_static: deviceInfo.DeviceInfoStatic, message_type: str, election_id: str) -> str:
    return f'election, {message_type}, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, electionId: {election_id}'


def request_heartbeat_message(device_info_static: deviceInfo.DeviceInfoStatic) -> str:
    return f'request, heartbeat, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}'


def response_heartbeat_message(device_info_static: deviceInfo.DeviceInfoStatic) -> str:
    return f'response, heartbeat, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}'


def get_file_transfer_message(device_info_static: deviceInfo.DeviceInfoStatic, message_type: str, filename: str, vector_clock: dict, original_sender_id: int) -> str:
    return f'update, {message_type}, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, originalSenderID: {original_sender_id}, <SEPARATOR>{filename}<SEPARATOR>{vector_clock}<SEPARATOR>'


def is_leader(message: str) -> bool:
    return message.split(',')[0] == "election" and message.split(',')[1] == " leader"


def is_response(message: str) -> bool:
    return message.split(',')[0] == "response"


def get_message_type(message: str) -> str:
    return message.split(',')[1].lstrip()


def get_sender_ip(message: str) -> str:
    return str(message.split(",")[2].split(':')[1].strip())


def get_sender_id(message: str) -> int:
    return int(message.split(',')[3].split(':')[1].strip())


def get_original_sender_id(message: str) -> int:
    #if "file transfer" in get_message_type(message):
    #    raise Exception
    return int(message.split(',')[4].split(':')[1].strip())


def get_sender_vector_clock(message: str) -> dict():
    if get_message_type(message) != "peer discovery":
        return ""#TODO
    message_dictionary = message.split("<SEPARATOR>")[1].split('{')[1].strip('}').strip().split(',')
    dictionary = dict()
    for entry in message_dictionary:
        if '' == entry:
            continue
        key = entry.split(':')[0]
        value = entry.split(':')[1]
        dictionary.update({int(key): int(value)})
    return dictionary
