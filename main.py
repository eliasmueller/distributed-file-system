import multiprocessing
import time

import bully_algorithm
import monitor_local_folder
import util
import discovery
import deviceInfo as deviceInfo
import broadcast_listener as bListen
import file_tcp_listener as fListen

def establish_listeners(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    listeners = []
    p_broadcast_listen = bListen.BroadcastListener(device_info_static, device_info_dynamic, shared_queue)
    listeners.append(p_broadcast_listen)
    p_broadcast_listen.start()

    p_file_listen = fListen.FileListener(device_info_static, device_info_dynamic, shared_queue)
    listeners.append(p_file_listen)
    p_file_listen.start()
    return listeners


def start_bully(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    p_bully = multiprocessing.Process(target=bully_algorithm.BullyAlgorithm, args=(device_info_static, device_info_dynamic, shared_queue))
    p_bully.daemon = True
    p_bully.start()
    return p_bully


def start_folder_monitor(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    p_monitor = multiprocessing.Process(target=monitor_local_folder.FolderMonitor, args=(device_info_static, device_info_dynamic, shared_queue))
    p_monitor.daemon = True
    p_monitor.start()
    return p_monitor


if __name__ == '__main__':
    device_info_static, device_info_dynamic = deviceInfo.lear_about_myself()

    shared_queue = multiprocessing.Queue()

    listeners = establish_listeners(device_info_static, device_info_dynamic, shared_queue)

    p_discovery = multiprocessing.Process(target=discovery.discover_peers, args=(device_info_static, device_info_dynamic, shared_queue))
    p_discovery.start()
    p_discovery.join()

    queue_message = util.consume(shared_queue)
    if isinstance(queue_message, deviceInfo.DeviceInfoDynamic):
        device_info_dynamic = queue_message
        device_info_dynamic.print_info()
        # Wait for initial discovery for now, then the view of the group should be established
        # TODO use proper observer pattern in order to update the group view in the subprocesses. Queue is suboptimal.
        p_bully = start_bully(device_info_static, device_info_dynamic, shared_queue)
        p_monitor = start_folder_monitor(device_info_static, device_info_dynamic, shared_queue)

    for listener in listeners:
        listener.join()
