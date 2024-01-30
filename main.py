import sys
import multiprocessing
from multiprocessing.managers import DictProxy

import bully_algorithm
import file_tcp_init_listener
import monitor_local_folder
import discovery
import deviceInfo as deviceInfo
import shared_dict_helper

import broadcast_listener as bListen
import file_tcp_listener as fListen
import file_tcp_r_multicast_listener as reliable_Listen
import file_tcp_o_multicast_listener as ordered_Listen

import heartbeat as hb


def establish_listeners(device_info_static: deviceInfo.DeviceInfoStatic,
                        device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                        shared_queue: multiprocessing.Queue,
                        shared_dict: DictProxy,
                        lock):
    listeners = []

    p_init_folder_listener = file_tcp_init_listener.FileInitListener(device_info_static, shared_dict, lock)
    listeners.append(p_init_folder_listener)
    p_init_folder_listener.start()

    p_broadcast_listen = bListen.BroadcastListener(device_info_static, device_info_dynamic, shared_queue, shared_dict, lock)
    listeners.append(p_broadcast_listen)
    p_broadcast_listen.start()

    r_deliver_queue = multiprocessing.Queue()
    o_deliver_queue = multiprocessing.Queue()

    p_reliable_multicast_listen = reliable_Listen.ReliableMulticastListener(device_info_static, device_info_dynamic, r_deliver_queue, shared_dict, lock)
    listeners.append(p_reliable_multicast_listen)
    p_reliable_multicast_listen.start()

    p_ordered_multicast_listen = ordered_Listen.OrderedMulticastListener(device_info_static, device_info_dynamic, r_deliver_queue, o_deliver_queue, shared_dict, lock)
    listeners.append(p_ordered_multicast_listen)
    p_ordered_multicast_listen.start()

    p_file_listen = fListen.FileListener(device_info_static, device_info_dynamic, o_deliver_queue, shared_dict, lock)
    listeners.append(p_file_listen)
    p_file_listen.start()

    return listeners


def start_bully(device_info_static: deviceInfo.DeviceInfoStatic,
                device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                shared_queue: multiprocessing.Queue,
                shared_dict: DictProxy,
                lock):
    p_bully = multiprocessing.Process(target=bully_algorithm.BullyAlgorithm, args=(device_info_static, device_info_dynamic, shared_queue, shared_dict, lock))
    p_bully.daemon = True
    p_bully.start()
    return p_bully


def start_folder_monitor(device_info_static: deviceInfo.DeviceInfoStatic,
                         device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                         shared_queue: multiprocessing.Queue,
                         shared_dict: DictProxy,
                         lock):
    p_monitor = multiprocessing.Process(target=monitor_local_folder.FolderMonitor, args=(device_info_static, device_info_dynamic, shared_queue, shared_dict, lock))
    p_monitor.daemon = True
    p_monitor.start()
    return p_monitor


def start_heartbeat(device_info_static,
                    shared_dict: DictProxy,
                    lock,
                    interval: int):
    heartbeat = multiprocessing.Process(target=hb.Heartbeat, args=(device_info_static, shared_dict, lock, interval))
    heartbeat.daemon = True
    heartbeat.start()
    return heartbeat


if __name__ == '__main__':
    if len(sys.argv) > 1:
        input_id = int(sys.argv[1])
        input_path = str(sys.argv[2])
        device_info_static, device_info_dynamic = deviceInfo.initialise_myself(input_id, input_path)
    else:
        device_info_static, device_info_dynamic = deviceInfo.initialise_myself()

    dynamic_manager = multiprocessing.Manager()
    lock = dynamic_manager.Lock()
    shared_device_info_dynamic = dynamic_manager.dict()
    shared_dict_helper.initialise_shared_dict(shared_device_info_dynamic, lock, device_info_dynamic)

    shared_queue = multiprocessing.Queue()

    listeners = establish_listeners(device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)

    p_discovery = multiprocessing.Process(target=discovery.discover_peers, args=(device_info_static, device_info_dynamic, shared_device_info_dynamic, lock))
    p_discovery.start()

    p_bully = start_bully(device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)

    heartbeat = start_heartbeat(device_info_static, shared_device_info_dynamic, lock, interval=5)

    p_discovery.join()
    p_monitor = start_folder_monitor(device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)

    # device_info_dynamic = shared_dict.get("device_info_dynamic")
    device_info_dynamic.get_update_from_shared_dict(shared_device_info_dynamic)
    device_info_dynamic.print_info()

    for listener in listeners:
        listener.join()
