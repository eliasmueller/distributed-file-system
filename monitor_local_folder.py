import multiprocessing
from multiprocessing.managers import DictProxy
import os
import time

import deviceInfo
import sender as bSend
import util
import shared_dict_helper
from shared_dict_helper import DictKey

class FolderMonitor:
    def __init__(self,
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 shared_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.shared_dict = shared_dict
        self.file_state = util.get_folder_state(self.device_info_static.MY_STORAGE)
        self.is_running = True
        self.lock = lock
        self.run()

    def check_folder_changes(self):
        # TODO supervise that changes triggered by remote updates are ignored
        assert self.device_info_dynamic is not None
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        self.file_state = self.device_info_dynamic.PEER_file_state
        current_state = util.get_folder_state(self.device_info_static.MY_STORAGE)

        added_files = [f for f in current_state if f not in self.file_state]
        deleted_files = [f for f in self.file_state if f not in current_state]
        modified_files = [f for f in current_state if current_state[f] != self.file_state.get(f, 0)]

        if added_files:
            self.notify_all_peers_about_file_change("add", added_files)
        if modified_files:
            self.notify_all_peers_about_file_change("modify", modified_files)
        if deleted_files:
            self.notify_all_peers_about_file_change("delete",deleted_files)

        self.file_state = current_state
        self.device_info_dynamic.PEER_file_state = self.file_state
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state, self.file_state)

    def run(self):
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state, self.file_state)
        try:
            while self.is_running:
                self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
                self.check_folder_changes()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def consistent_ordered_multicast_file_change(self, message_type, f):
        #this is the start of the sending process for a ordered multicast
        #increase own vector clock entry
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        self.device_info_dynamic.increase_vector_clock_entry(self.device_info_static.PEER_ID, 1)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_vector_clock, self.device_info_dynamic.PEER_vector_clock)
        bSend.reliable_multicast(self.device_info_static, self.device_info_dynamic, message_type, f)

    def notify_all_peers_about_file_change(self, message_type, files):
        print(f"Change detected: {message_type}, {files}")
        for f in files:
            if f.startswith("."):  # Working files could often start with "." we do not want to send this.
                continue
            if f.startswith("tempversion_"):  # not deliver file changes start with "tempversion_" we do not want to send this.
                continue
            if f.startswith("lock_"):  # to lock a file another file with same name and the prefix lock_ is created.
                if message_type == "add":
                    self.lock_file(f)
                elif message_type == "delete":
                    self.unlock_file(f.split("lock_")[1], discard=True)
                continue
            if self.file_is_locked(f):
                if not self.unlock_file(f, discard=False):
                    continue
            print(f"sending {f}")
            self.consistent_ordered_multicast_file_change(message_type, f)

    def file_is_locked(self, filename: str):
        return filename in self.device_info_dynamic.LOCKED_FILES.keys()

    def lock_file(self, filename: str):
        file = filename.split("lock_")[1]
        filepath = f"{self.device_info_static.MY_STORAGE}/{file}"
        if os.path.exists(filepath):
            print(f"Locking file {file} locally.")
            self.device_info_dynamic.LOCKED_FILES[file] = "none"
            self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
        else:
            os.remove(f"{self.device_info_static.MY_STORAGE}/{filename}")

    def unlock_file(self, filename: str, discard: bool) -> bool:
        if not discard:  # when the lock file is deleted we don't delete anything else
            filepath = f"{self.device_info_static.MY_STORAGE}/lock_{filename}"
            os.remove(filepath)
        if discard or self.device_info_dynamic.LOCKED_FILES[filename] != "remote":  # if there has been no remote change we simply continue
            print(f"Unlocking file {filename} locally.")
            return_val = True
        else: # remote and local changes -> has to be merged manually
            print(f"File has been edited remotely, please merge locally, your changes will be found in .mod_{filename}.")
            os.system(f"cp {self.device_info_static.MY_STORAGE}/{filename} {self.device_info_static.MY_STORAGE}/.mod_{filename}")
            return_val = False
        if filename in self.device_info_dynamic.LOCKED_FILES.keys():
            del self.device_info_dynamic.LOCKED_FILES[filename]
            self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
        return return_val
