import multiprocessing
import sys
from multiprocessing.managers import DictProxy

import broadcast_listener as b_listen
import bully_algorithm
import device_info
import discovery
import file_tcp_init_listener
import file_tcp_listener as f_listen
import file_tcp_o_multicast_listener as ordered_listen
import file_tcp_r_multicast_listener as reliable_listen
import heartbeat as hb
import monitor_local_folder
import shared_dict_helper


def establish_listeners(_device_info_static: device_info.DeviceInfoStatic,
                        _device_info_dynamic: device_info.DeviceInfoDynamic,
                        _shared_queue: multiprocessing.Queue,
                        _shared_dict: DictProxy,
                        _lock):
    _listeners = []

    p_init_folder_listener = file_tcp_init_listener.FileInitListener(_device_info_static, _shared_dict, _lock)
    _listeners.append(p_init_folder_listener)
    p_init_folder_listener.start()

    p_broadcast_listen = b_listen.BroadcastListener(
        _device_info_static, _device_info_dynamic, _shared_queue, _shared_dict, _lock)
    _listeners.append(p_broadcast_listen)
    p_broadcast_listen.start()

    r_deliver_queue = multiprocessing.Queue()
    o_deliver_queue = multiprocessing.Queue()

    p_reliable_multicast_listen = reliable_listen.ReliableMulticastListener(
        _device_info_static, _device_info_dynamic, r_deliver_queue, _shared_dict, _lock)
    _listeners.append(p_reliable_multicast_listen)
    p_reliable_multicast_listen.start()

    p_ordered_multicast_listen = ordered_listen.OrderedMulticastListener(
        _device_info_static, _device_info_dynamic, r_deliver_queue, o_deliver_queue, _shared_dict, _lock)
    _listeners.append(p_ordered_multicast_listen)
    p_ordered_multicast_listen.start()

    p_file_listen = f_listen.FileListener(
        _device_info_static, _device_info_dynamic, o_deliver_queue, _shared_dict, _lock)
    _listeners.append(p_file_listen)
    p_file_listen.start()

    return _listeners


def start_bully(_device_info_static: device_info.DeviceInfoStatic,
                _device_info_dynamic: device_info.DeviceInfoDynamic,
                _shared_queue: multiprocessing.Queue,
                _shared_dict: DictProxy,
                _lock):
    _p_bully = multiprocessing.Process(target=bully_algorithm.BullyAlgorithm, args=(
        _device_info_static, _device_info_dynamic, _shared_queue, _shared_dict, _lock))
    _p_bully.daemon = True
    _p_bully.start()
    return _p_bully


def start_folder_monitor(_device_info_static: device_info.DeviceInfoStatic,
                         _device_info_dynamic: device_info.DeviceInfoDynamic,
                         _shared_queue: multiprocessing.Queue,
                         _shared_dict: DictProxy,
                         _lock):
    _p_monitor = multiprocessing.Process(target=monitor_local_folder.FolderMonitor, args=(
        _device_info_static, _device_info_dynamic, _shared_queue, _shared_dict, _lock))
    _p_monitor.daemon = True
    _p_monitor.start()
    return _p_monitor


def start_heartbeat(_device_info_static,
                    _shared_dict: DictProxy,
                    _lock,
                    _interval: int):
    _heartbeat = multiprocessing.Process(target=hb.Heartbeat, args=(
        _device_info_static, _shared_dict, _lock, _interval))
    _heartbeat.daemon = True
    _heartbeat.start()
    return _heartbeat


if __name__ == '__main__':
    if len(sys.argv) > 1:
        input_id = int(sys.argv[1])
        input_path = str(sys.argv[2])
        device_info_static, device_info_dynamic = device_info.initialise_myself(input_id, input_path)
    else:
        device_info_static, device_info_dynamic = device_info.initialise_myself()

    dynamic_manager = multiprocessing.Manager()
    lock = dynamic_manager.Lock()
    shared_device_info_dynamic = dynamic_manager.dict()
    shared_dict_helper.initialise_shared_dict(shared_device_info_dynamic, lock, device_info_dynamic)

    shared_queue = multiprocessing.Queue()

    listeners = establish_listeners(
        device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)

    p_discovery = multiprocessing.Process(target=discovery.discover_peers, args=(
        device_info_static, device_info_dynamic, shared_device_info_dynamic, lock))
    p_discovery.start()

    heartbeat = start_heartbeat(device_info_static, shared_device_info_dynamic, lock, _interval=5)

    p_discovery.join()

    # start monitoring file changes and elections after discovery
    p_monitor = start_folder_monitor(
        device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)
    p_bully = start_bully(device_info_static, device_info_dynamic, shared_queue, shared_device_info_dynamic, lock)

    # device_info_dynamic = shared_dict.get("device_info_dynamic")
    device_info_dynamic.get_update_from_shared_dict(shared_device_info_dynamic)
    device_info_dynamic.print_info()

    for listener in listeners:
        listener.join()
