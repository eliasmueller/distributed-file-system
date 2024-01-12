import multiprocessing
from multiprocessing.sharedctypes import Array

import bully_algorithm
import util
import discovery
import deviceInfo as deviceInfo
import listener as bListen
import heartbeat 

def establish_listeners(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    listeners = []
    p_Listen = bListen.BroadcastListener(device_info_static, device_info_dynamic, shared_queue)
    listeners.append(p_Listen)
    p_Listen.start()
    return listeners


def start_bully(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    p_bully = multiprocessing.Process(target=bully_algorithm.BullyAlgorithm, args=(device_info_static, device_info_dynamic, shared_queue))
    p_bully.daemon = True
    p_bully.start()
    return p_bully


if __name__ == '__main__':
    device_info_static, device_info_dynamic = deviceInfo.lear_about_myself()

    leader_ip_shared = multiprocessing.Array('c', b'unavailable', lock=False)
    shared_queue = multiprocessing.Queue()

    p_bully = start_bully(device_info_static, device_info_dynamic, shared_queue)

    listeners = establish_listeners(device_info_static, device_info_dynamic, shared_queue)

    p_discovery = multiprocessing.Process(target=discovery.discover_peers, args=(device_info_static, device_info_dynamic, shared_queue))
    p_discovery.start()
    p_discovery.join()

    heartbeat.send_heartbeat_to_leader(device_info_static, device_info_dynamic)

    for listener in listeners:
        listener.join()

    queue_message = util.consume(shared_queue)
    if isinstance(queue_message, deviceInfo.DeviceInfoDynamic):
        device_info_dynamic = queue_message
        device_info_dynamic.print_info()

    print("leader ip = ") 
    print(leader_ip_shared.value)