import multiprocessing
import os
import shutil
from multiprocessing.managers import DictProxy

import device_info
import shared_dict_helper
import util
from shared_dict_helper import DictKey

BUFFER_SIZE = 4096


class FileListener(multiprocessing.Process):
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 device_info_dynamic: device_info.DeviceInfoDynamic,
                 deliver_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        super(FileListener, self).__init__()
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.o_deliver_queue = deliver_queue
        self.shared_dict = shared_dict
        self.isRunning = True
        self.hold_back_queue = []
        self.lock = lock
        self.hold_back_locked_files = []

    def run(self):
        print("Listening for ordered reliable multicast delivery to signal file changes")
        self.file_change_listener()

    def file_change_listener(self):
        # is waiting until it receives something and can not be exited with KeyboardInterrupt
        while self.isRunning:
            try:
                self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
                if self.hold_back_locked_files:
                    for (file_name, temp_filename, message_type, vector_clock) in self.hold_back_locked_files:
                        if not self.check_locked_file(file_name):
                            self.update_file_from_tempfile(file_name, temp_filename, message_type, vector_clock)
                # receive ordered reliable multicast delivery
                (file_name, temp_filename, message_type, vector_clock) = self.o_deliver_queue.get()
                # application has message
                if temp_filename:
                    self.update_device_info_dynamic()
                    if self.check_locked_file(file_name):
                        self.hold_back_locked_files.append((file_name, temp_filename, message_type, vector_clock))
                        print(f"Not applying received file changes because file is locked locally.")
                    else:
                        print(f"Received file changes")
                        if message_type == "delete":
                            util.delete_file(file_name, self.device_info_static.MY_STORAGE)
                            util.delete_file(temp_filename, self.device_info_static.MY_STORAGE)
                        else:
                            self.update_file_from_tempfile(file_name, temp_filename, self.device_info_static.MY_STORAGE,
                                                           vector_clock)
                        self.update_device_info_dynamic()

            except KeyboardInterrupt:
                self.isRunning = False
            except Exception:
                continue

    def update_file_from_tempfile(self, filename: str, temp_filename: str, storage_path: str, vector_clock: dict):
        # override file
        filepath_file = f"{storage_path}/{filename}"
        filepath_temp = f"{storage_path}/{temp_filename}"

        # each peer should be able to retransmit any lost message he delivered
        filename_sender_temp = f".tempversion_sender_{util.vector_clock_to_path_string(vector_clock)}_{filename}"
        filepath_temp_sender = f"{storage_path}/{filename_sender_temp}"
        shutil.copy(filepath_temp, filepath_temp_sender)

        os.replace(filepath_temp, filepath_file)

    def update_device_info_dynamic(self):
        # update monitor last file change view
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state,
                                              util.get_folder_state(self.device_info_static.MY_STORAGE))

    def check_locked_file(self, filename) -> bool:
        # If a file is locked we keep everything in the hold back queue until unlocked again to ensure consistency
        if filename in self.device_info_dynamic.LOCKED_FILES.keys():
            print(f"Received change for locked file {filename}, holding it back in the queue.")
            self.device_info_dynamic.LOCKED_FILES[filename] = "remote"
            self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
            return True
        else:
            return False
