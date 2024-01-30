import ast
import multiprocessing
import message_formater
from multiprocessing.managers import DictProxy
from shared_dict_helper import DictKey
import deviceInfo
import shared_dict_helper


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
            shared_dict_helper.update_shared_dict(shared_dict, lock, shared_dict_helper.DictKey.peer_ip_dict, peer_ip_dict)
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
            message_formater.election_extractor(message_specification, sender_id, election_id, message_sender_ip, shared_queue)
        pass
    elif message_type == 'ACK':
        pass
    else:
        pass
    return ''


def request_answerer(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                     message_specification: str) -> str:
    if message_specification == ' peer discovery':
        return message_formater.response_discovery(device_info_static, device_info_dynamic)
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