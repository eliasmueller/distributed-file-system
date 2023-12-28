import multiprocessing
# import ast #Abstract Syntax Trees
from typing import List

import util
import deviceInfo as deviceInfo
import sender as bSend
import messageFormater as formater


def discover_peers(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                   shared_queue: multiprocessing.Queue):
    # Send broadcast message
    # message = device_info.MY_IP + ' sent a broadcast message'
    # p_send = multiprocessing.Process(target=bSend.broadcast, args=(device_info.LAN_BOADCAST_IP, device_info.LAN_BROADCAST_PORT, message))
    # p_send_leader = multiprocessing.Process(target=bSend.discover_leaders, args=(device_info))
    # p_send_peer = multiprocessing.Process(target=bSend.discover_peers, args=(device_info))
    # p_send_leader.start()
    # p_send_peer.start()
    # p_send_leader.join()
    # p_send_peer.join()

    # discover peers
    message = formater.request_discovery(device_info_static, device_info_dynamic)
    bSend.basic_broadcast(device_info_static.LAN_BROADCAST_IP, device_info_static.LAN_BROADCAST_PORT, str(message))
    answers = []
    while True:
        answer = bSend.listen_for_answer(1)
        if answer is None:
            break
        answers.append(answer)
        # print(f"recieved answer {answer}")

    # update group view
    new_peer_view = interpret_discovery_answers(device_info_static, answers)
    device_info_dynamic.update_peer_view(new_peer_view)

    # broadcast collected group view to update als views of other peers
    message = formater.update_peer_view(device_info_static, device_info_dynamic)
    bSend.basic_broadcast(device_info_static.LAN_BROADCAST_IP, device_info_static.LAN_BROADCAST_PORT, str(message))
    util.produce_device_info_dynamic(shared_queue, device_info_dynamic)


def interpret_discovery_answers(device_info_static: deviceInfo.DeviceInfoStatic, answers: List[str]) -> []:
    # TODO resolve if not all answers are similar
    new_peer_view = {}
    for answer in answers:
        new_peer_view[formater.get_sender_id(answer)] = formater.get_sender_ip(answer)
        # answer_peer_view = formater.process_message()
        # new_peer_view = ast.literal_eval(answer_peer_view)
    if device_info_static.PEER_ID not in new_peer_view:
        # TODO if two times in list then network duplicates or ID already used
        new_peer_view[device_info_static.PEER_ID] = device_info_static.MY_IP
    return new_peer_view
