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
                self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
                #recieve ordered reliable multicast delivery
                file_name, temp_filename, message_type = self.o_deliver_queue.get()
                #application has message
                if temp_filename:
                    print(f"Received file changes {message_type}")
                    if message_type == " file transfer delete":
                        util.delete_file(file_name, self.device_info_static.MY_STORAGE)
                        util.delete_file(temp_filename, self.device_info_static.MY_STORAGE)
                    else:
                        self.update_file_from_tempfile(file_name, temp_filename, self.device_info_static.MY_STORAGE)
                    self.update_device_info_dynamic()

            except KeyboardInterrupt:
                self.isRunning = False
            # TODO proper exception handling
            except Exception:
                continue

    def update_file_from_tempfile(self, filename: str, temp_filename: str, storage_path: str):
        #override file
        filepath_file = f"{storage_path}/{filename}"
        filepath_temp = f"{storage_path}/{temp_filename}"
        
        os.replace(filepath_temp, filepath_file)

    def update_device_info_dynamic(self):
        #update monitor last file change view
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        self.device_info_dynamic.PEER_file_state = util.get_folder_state(self.device_info_static.MY_STORAGE)
        self.shared_dict.update(device_info_dynamic = self.device_info_dynamic)
