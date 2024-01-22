import socket
import multiprocessing
import os

import file_transfer
import deviceInfo as deviceInfo
import util

buffer_size = 4096


class FileListener(multiprocessing.Process):
    def __init__(self, 
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic, 
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy):
        super(FileListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.o_deliver_queue = deliver_queue
        self.shared_dict = shared_dict
        self.isRunning = True

    def run(self):
        print("Listening for ordered reliable multicast delivery to signal file changes")
        self.file_change_listener()

    def file_change_listener(self):
        # is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.update_device_info_dynamic()
                if not self.o_deliver_queue.empty(): #TODO change to blocking check instead of spinning empty check
                    #recieve ordered reliable multicast delivery
                    file_name, temp_filename, message_type = self.o_deliver_queue.get()
                    #application has message
                    if temp_filename:
                        print(f"Received file changes")
                        self.update_file_from_tempfile(file_name, temp_filename, message_type)
            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def update_file_from_tempfile(self, filename: str, temp_filename: str, message_type: str):
        #override file
        filepath_file = f"{self.device_info_static.MY_STORAGE}/{filename}"
        filepath_temp = f"{self.device_info_static.MY_STORAGE}/{temp_filename}"
        if message_type == " file transfer delete":
            if os.path.exists(filepath_file):
                os.remove(filepath_file)
            if os.path.exists(filepath_temp):
                os.remove(filepath_temp)
        else:
            os.replace(filepath_temp, filepath_file)

        #update monitor last file change view
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        self.device_info_dynamic.PEER_file_state = util.get_folder_state(self.device_info_static.MY_STORAGE)
        self.shared_dict.update(device_info_dynamic = self.device_info_dynamic)
                
    def update_device_info_dynamic(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
