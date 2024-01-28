# functions to abstract message syntax out of the code
import ast
import multiprocessing
from multiprocessing.managers import DictProxy
import pickle
from typing import List

import deviceInfo as deviceInfo
import electionMessage as electionMessage
import util
import shared_dict_helper
from shared_dict_helper import DictKey


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
    return f'update, file transfer {message_type}, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, originalSenderID: {original_sender_id}, <SEPARATOR>{filename}<SEPARATOR>{vector_clock}<SEPARATOR>'


# answer extractor

def process_message(device_info_static: deviceInfo.DeviceInfoStatic,
                    device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                    message: str,
                    shared_queue: multiprocessing.Queue,
                    shared_dict: DictProxy,
                    lock) -> str:
    message_split = message.split(',')
    message_type = message_split[0]
    message_specification = message_split[1]
    message_sender_ip = message_split[2].split(':')[1].strip()
    message_sender_id = message_split[3].split(':')[1].strip()
    message_payload = message_split[4].split(':')[1].strip()
    if message_type == 'request':
        return request_answerer(device_info_static, device_info_dynamic, message_specification)
    elif message_type == 'response':
        return response_extractor(message_specification, message_payload)
    elif message_type == 'update':
        peer_id = int(message_sender_id)
        peers = shared_dict[DictKey.peers.value]
        peer_ip_dict = shared_dict[DictKey.peer_ip_dict.value]
        if peer_id not in peers:
            peers.append(peer_id)
            peer_ip_dict[peer_id] = message_sender_ip
            shared_dict_helper.update_shared_dict(shared_dict, lock, DictKey.peer_ip_dict, peer_ip_dict)
            shared_dict_helper.update_shared_dict(shared_dict, lock, DictKey.peers, peers)
            print(f"Updating known peers: {peers}")
        return 'ACK, update'
    # this message type is used by the leader to notify the group about dead peers
    elif message_type == 'remove':
        if device_info_dynamic.LEADER_ID != device_info_static.PEER_ID:
            peers = ast.literal_eval(message_payload)
            dead_peers = peers
            for dead_id in dead_peers:
                device_info_dynamic.PEERS.remove(dead_id)
                del device_info_dynamic.PEER_IP_DICT[dead_id]
            print(f"Removing known peers as defined by leader. New group view: {device_info_dynamic.PEERS} ")
            device_info_dynamic.update_entire_shared_dict(shared_dict, lock)
    elif message_type == 'election':
        election_id = message_payload
        sender_id = int(message_sender_id)
        if device_info_static.PEER_ID != sender_id:
            election_extractor(message_specification, sender_id, election_id, message_sender_ip, shared_queue)
        pass
    elif message_type == 'ACK':
        pass
    else:
        pass
    return ''


def election_extractor(message_specification: str, message_sender_id: int, election_id: str, sender_ip: str,
                       shared_queue: multiprocessing.Queue):
    election_message = electionMessage.ElectionMessage(sender_id=message_sender_id,
                                                       message_specification=message_specification,
                                                       election_id=election_id,
                                                       sender_ip=sender_ip)
    util.produce_election_message(shared_queue, election_message)


def request_answerer(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                     message_specification: str) -> str:
    if message_specification == ' peer discovery':
        return response_discovery(device_info_static, device_info_dynamic)
    # elif message_specification == 'ACK':
    #    return f'response, ACK, senderIP: {device_info.MY_IP}, senderID: {device_info.PEER_ID}, senderView: {device_info.PEERS}' 
    else:
        pass
    return ''  # to send no answer


def response_extractor(message_specification: str, message_payload: str) -> str:
    if message_specification == ' peer discovery':
        # returns the array of peers as a string
        return message_payload
    # elif message_specification == 'ACK':
    #    pass
    else:
        pass
    return ''  # empty answer no further investigation needed


def is_leader(message: str) -> bool:
    return message.split(',')[0] == "election" and message.split(',')[1] == " leader"


def is_response(message: str) -> bool:
    return message.split(',')[0] == "response"


def get_message_type(message: str) -> str:
    return message.split(',')[1]


def get_sender_ip(message: str) -> str:
    return str(message.split(",")[2].split(':')[1].strip())


def get_sender_id(message: str) -> int:
    return int(message.split(',')[3].split(':')[1].strip())


def get_original_sender_id(message: str) -> int:
    if "file transfer" in get_message_type(message):
        raise Exception
    return int(message.split(',')[4].split(':')[1].strip())


def get_sender_vector_clock(message: str) -> dict():
    if get_message_type(message) != " peer discovery":
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
