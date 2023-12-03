import multiprocessing

import util
import discovery
import deviceInfo as deviceInfo
import listener as bListen


def establisch_listeners(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
    listeners = []
    p_Listen = bListen.BroadcastListener(device_info_static, device_info_dynamic, shared_queue)
    listeners.append(p_Listen)
    p_Listen.start()
    return listeners

if __name__ == '__main__':
    device_info_static, device_info_dynamic = deviceInfo.lear_about_myself()

    shared_queue = multiprocessing.Queue()

    listeners = establisch_listeners(device_info_static, device_info_dynamic, shared_queue)

    p_discovery = multiprocessing.Process(target=discovery.discoverPeers, args=(device_info_static, device_info_dynamic, shared_queue))
    p_discovery.start()
    p_discovery.join()
    device_info_dynamic = util.consume(shared_queue)
    device_info_dynamic.print_info()

    #end of programm
    for listener in listeners:
        listener.join()

