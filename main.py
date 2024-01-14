import multiprocessing
import time
from multiprocessing.managers import DictProxy

import bully_algorithm
import monitor_local_folder
import util
import discovery
import deviceInfo as deviceInfo
import broadcast_listener as bListen
import file_tcp_listener as fListen

def establish_listeners(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue, shared_dict: DictProxy):
    listeners = []
    p_broadcast_listen = bListen.BroadcastListener(device_info_static, device_info_dynamic, shared_queue, shared_dict)
    listeners.append(p_broadcast_listen)
    p_broadcast_listen.start()

    p_file_listen = fListen.FileListener(device_info_static, device_info_dynamic, shared_queue, shared_dict)
    listeners.append(p_file_listen)
    p_file_listen.start()
    return listeners


def start_bully(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue, shared_dict: DictProxy):
    p_bully = multiprocessing.Process(target=bully_algorithm.BullyAlgorithm, args=(device_info_static, device_info_dynamic, shared_queue, shared_dict))
    p_bully.daemon = True
    p_bully.start()
    return p_bully


def start_folder_monitor(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue, shared_dict: DictProxy):
    p_monitor = multiprocessing.Process(target=monitor_local_folder.FolderMonitor, args=(device_info_static, device_info_dynamic, shared_queue, shared_dict))
    p_monitor.daemon = True
    p_monitor.start()
    return p_monitor


if __name__ == '__main__':
    device_info_static, device_info_dynamic = deviceInfo.lear_about_myself()

    with multiprocessing.Manager() as dynamic_manager:
        shared_dict = dynamic_manager.dict({'device_info_dynamic': device_info_dynamic, 'device_info_static': device_info_static})

        shared_queue = multiprocessing.Queue()

        listeners = establish_listeners(device_info_static, device_info_dynamic, shared_queue, shared_dict)

        p_discovery = multiprocessing.Process(target=discovery.discover_peers, args=(device_info_static, device_info_dynamic, shared_queue, shared_dict))
        p_discovery.start()

        p_bully = start_bully(device_info_static, device_info_dynamic, shared_queue, shared_dict)
        p_monitor = start_folder_monitor(device_info_static, device_info_dynamic, shared_queue, shared_dict)

        p_discovery.join()

        shared_dict.get("device_info_dynamic").print_info()

        for listener in listeners:
            listener.join()
