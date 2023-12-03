#functions to abstract message syntax out of the code
import deviceInfo as deviceInfo

def request_discovery(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'request, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'

def response_discovery(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'response, peer discovery, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'

def update_peer_view(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic) -> str:
    return f'update, peer view, senderIP: {device_info_static.MY_IP}, senderID: {device_info_static.PEER_ID}, senderView: {device_info_dynamic.PEERS}'



#answer extractor

def process_message(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, message: str) -> str:
    message_split = message.split(',')
    message_type = message_split[0]
    message_specivication = message_split[1]
    message_senderIP = message_split[2].split(':')[1].strip()
    message_senderID = message_split[3].split(':')[1].strip()
    message_payload = message_split[4]
    if message_type == 'request':
        return request_answerer(device_info_static, device_info_dynamic, message_specivication)
    elif message_type == 'response':
        return response_extractor(message_specivication, message_payload)
    elif message_type == 'update':
        return 'ACK, update'
    elif message_type == 'ACK':
        pass
    else:
        pass
    return ''

def request_answerer(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, message_specivication: str) -> str:
    if message_specivication == ' peer discovery':
        return response_discovery(device_info_static, device_info_dynamic)
    #elif message_specivication == 'ACK':
    #    return f'response, ACK, senderIP: {device_info.MY_IP}, senderID: {device_info.PEER_ID}, senderView: {device_info.PEERS}' 
    else:
        pass
    return '' #to send no answer

def response_extractor(message_specivication: str, message_payload: str) -> str:
    if message_specivication == ' peer discovery':
        #returns the array of peers as a string
        return message_payload.split(':')[1]
    #elif message_specivication == 'ACK':
    #    pass
    else:
        pass
    return '' #empty answer no further investigation needed

def get_sender_ID(message: str) -> int:
    return int(message.split(',')[3].split(':')[1].strip())





        