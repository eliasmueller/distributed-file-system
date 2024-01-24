import multiprocessing
from multiprocessing.managers import DictProxy
# import ast #Abstract Syntax Trees
from typing import List

import util
import deviceInfo as deviceInfo
import sender as bSend
import message_formater as formater
import util

def discover_peers(device_info_static: deviceInfo.DeviceInfoStatic,
                   device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                   shared_dict: DictProxy,
                   lock):
    # discover peers
    print("start a discovery")
    message = formater.request_discovery(device_info_static, device_info_dynamic)
    bSend.basic_broadcast(device_info_static.LAN_BROADCAST_IP, device_info_static.LAN_BROADCAST_PORT, str(message))
    answers = []
    while True:
        answer = bSend.listen_for_broadcast_answer(3)
        if answer is None:
            break
        answers.append(answer)
        # print(f"recieved answer {answer}")

    # update group view
    new_peer_view, leader_id, new_vector_clock = interpret_discovery_answers(device_info_static, answers)
    device_info_dynamic.update_peer_view(new_peer_view)
    device_info_dynamic.update_vector_clock(new_vector_clock)
    if leader_id:
        device_info_dynamic.LEADER_ID = leader_id

    # broadcast collected group view to update als views of other peers
    message = formater.update_peer_view(device_info_static, device_info_dynamic)
    bSend.basic_broadcast(device_info_static.LAN_BROADCAST_IP, device_info_static.LAN_BROADCAST_PORT, str(message))
    device_info_dynamic.update_entire_shared_dict(shared_dict, lock)

def interpret_discovery_answers(device_info_static: deviceInfo.DeviceInfoStatic, answers: List[str]):
    # TODO resolve if not all answers are similar
    new_peer_view = {}
    new_vector_clock = dict()
    leader_id = None
    for answer in answers:
        sender_id = formater.get_sender_id(answer)
        if formater.is_leader(answer):
            leader_id = sender_id
        elif formater.is_response(answer):
            new_peer_view[sender_id] = formater.get_sender_ip(answer)
            # answer_peer_view = formater.process_message()
            # new_peer_view = ast.literal_eval(answer_peer_view)
        new_vector_clock.update({sender_id : util.get_or_default(formater.get_sender_vector_clock(answer), str(sender_id))})
        #TODO if other peers know the uuid of this peer with a vector clock > 0 we runn in a loop > discovery message resets vector clock of new id?
    if device_info_static.PEER_ID not in new_peer_view:
        # TODO if two times in list then network duplicates or ID already used
        new_peer_view[device_info_static.PEER_ID] = device_info_static.MY_IP
    return new_peer_view, leader_id, new_vector_clock
