import socket
import multiprocessing
import os
import time

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
        self.hold_back_queue = []
        self.hold_back_locked_files = []

    def run(self):
        print("Listening for ordered reliable multicast delivery to signal file changes")
        self.file_change_listener()

    def file_change_listener(self):
        # is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
                if self.hold_back_locked_files:
                    for (file_name, temp_filename, message_type) in self.hold_back_locked_files:
                        if not self.check_locked_file(file_name):
                            self.update_file_from_tempfile(file_name, temp_filename, message_type)
                #recieve ordered reliable multicast delivery
                file_name, temp_filename, message_type = self.o_deliver_queue.get()
                #application has message
                if temp_filename:
                    if self.check_locked_file(file_name):
                        self.hold_back_locked_files.append((file_name, temp_filename, message_type))
                        print(f"Not applying received file changes because file is locked locally.")
                    else:
                        print(f"Received file changes")
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

    def check_locked_file(self, filename) -> bool:
        # If a file is locked we keep everything in the hold back queue until unlocked again to ensure consistency and mark the file as remote edited
        if filename in self.device_info_dynamic.LOCKED_FILES.keys():
            print(f"Received change for locked file {filename}, holding it back in the queue.")
            self.device_info_dynamic.LOCKED_FILES[filename] = "remote"
            self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)
            return True
        else:
            return False
