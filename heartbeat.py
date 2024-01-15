import multiprocessing
import time
import threading
import deviceInfo
import sender as bSend

def send_heartbeat(device_info_static: deviceInfo.DeviceInfoStatic, interval=5):
    while True:
        bSend.basic_broadcast(ip=device_info_static.LAN_BROADCAST_IP, port=device_info_static.LAN_BROADCAST_PORT, message="heartbeat, something, senderIP: 192.168.178.70, senderID: something, hello there")
        print(f"Heartbeat sent to peer")
        time.sleep(interval)

    #threading.Thread(target=heartbeat_task, daemon=True).start()
        
def send_heartbeat_to_leader(device_info_static: deviceInfo.DeviceInfoStatic, device_info_dynamic: deviceInfo.DeviceInfoDynamic, interval=5):
    while True:
        device_info_dynamic.
        leader_ip = ""
        leader_port = ""
        bSend.basic_unicast(ip=, port=, message="heartbeat, something, senderIP: 192.168.178.70, senderID: something, hello there")
        # bSend.basic_broadcast(ip=device_info_static.LAN_BROADCAST_IP, port=device_info_static.LAN_BROADCAST_PORT, message="heartbeat, something, senderIP: 192.168.178.70, senderID: something, hello there")
        print(f"Heartbeat sent to peer")
        time.sleep(interval)

