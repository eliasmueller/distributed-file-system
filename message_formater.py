# functions to abstract message syntax out of the code
import multiprocessing

import deviceInfo as deviceInfo
import electionMessage as electionMessage
import util


def request_discovery(device_info_static: deviceInfo.DeviceInfoStatic,
                      device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'request, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'


def response_discovery(device_info_static: deviceInfo.DeviceInfoStatic,
                       device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'response, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'


def update_peer_view(device_info_static: deviceInfo.DeviceInfoStatic,
                     device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'update, peer view, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'


def get_election_message(device_info_static: deviceInfo.DeviceInfoStatic, message_type: str, election_id: str) -> str:
    return f'election, {message_type}, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, electionId: {election_id}'


# answer extractor

def process_message(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                    message: str, shared_queue: multiprocessing.Queue, shared_dict: multiprocessing.managers.DictProxy) -> str:
    message_split = message.split(',')
    message_type = message_split[0]
    message_specification = message_split[1]
    message_sender_ip = message_split[2].split(':')[1].strip()
    message_sender_id = message_split[3].split(':')[1].strip()
    message_payload = message_split[4]
    if message_type == 'request':
        return request_answerer(device_info_static, device_info_dynamic, message_specification)
    elif message_type == 'response':
        return response_extractor(message_specification, message_payload)
    elif message_type == 'update':
        peer_id = int(message_sender_id)
        if peer_id not in device_info_dynamic.PEERS:
            device_info_dynamic.append_new_peer(peer_id, message_sender_ip)
            shared_dict.update(device_info_dynamic=device_info_dynamic)
        return 'ACK, update'
    elif message_type == 'election':
        election_id = message_payload.split(':')[1].strip()
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
        return message_payload.split(':')[1]
    # elif message_specification == 'ACK':
    #    pass
    else:
        pass
    return ''  # empty answer no further investigation needed


def is_leader(message: str) -> bool:
    return message.split(':')[0] == "election" and message.split(':')[1] == "leader"


def is_response(message: str) -> bool:
    return message.split(':')[0] == "response"


def get_sender_id(message: str) -> int:
    return int(message.split(',')[3].split(':')[1].strip())


def get_sender_ip(message: str) -> str:
    return str(message.split(",")[2].split(':')[1].strip())
