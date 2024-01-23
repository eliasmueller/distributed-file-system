import multiprocessing
import os
import time

import deviceInfo
import sender as bSend
import util

class FolderMonitor:
    def __init__(self,
                 device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic,
                 shared_queue: multiprocessing.Queue,
                 shared_dict: multiprocessing.managers.DictProxy):
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
        self.shared_dict = shared_dict
        self.file_state = util.get_folder_state(self.device_info_static.MY_STORAGE)
        self.is_running = True

        self.device_info_dynamic.PEER_file_state = self.file_state
        self.shared_dict.update(device_info_dynamic = self.device_info_dynamic)

        self.run()

    def check_folder_changes(self):
        # TODO supervise that changes triggered by remote updates are ignored
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
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
        self.shared_dict.update(device_info_dynamic = self.device_info_dynamic)


    def run(self):
        try:
            while self.is_running:
                self.update_from_queue()
                self.check_folder_changes()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def consistent_ordered_multicast_file_change(self, message_type, f): 
        #increase own vector clock entry
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
        self.device_info_dynamic.increase_vector_clock_entry(self.device_info_static.PEER_ID, 1)
        self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)
        # TODO instead of (iterating over peers tcp) B multicast use (tcp) R multicast
        bSend.basic_multicast(self.device_info_static, self.device_info_dynamic, message_type, f)

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
                continue
            if self.file_is_locked(f):
                if not self.unlock_file(f):
                    continue
            print(f"sending {f}")
            self.consistent_ordered_multicast_file_change(message_type, f)
                
    def update_from_queue(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")

    def file_is_locked(self, filename: str):
        return filename in self.device_info_dynamic.LOCKED_FILES.keys()

    def lock_file(self, filename: str):
        file = filename.split("lock_")[1]
        filepath = f"{self.device_info_static.MY_STORAGE}/{file}"
        if os.path.exists(filepath):
            print(f"Locking file {file} locally. File can only be unlocked by saving/editing it.")
            self.device_info_dynamic.LOCKED_FILES[file] = "none"
            self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)
        else:
            os.remove(f"{self.device_info_static.MY_STORAGE}/{filename}")

    def unlock_file(self, filename: str) -> bool:
        filepath = f"{self.device_info_static.MY_STORAGE}/lock_{filename}"
        os.remove(filepath)
        self.shared_dict.update(device_info_dynamic=self.device_info_dynamic)

        if self.device_info_dynamic.LOCKED_FILES[filename] != "remote":
            del self.device_info_dynamic.LOCKED_FILES[filename]
            print(f"Unlocking file {filename} locally.")
            return True
        else:
            del self.device_info_dynamic.LOCKED_FILES[filename]
            print(f"File has been edited remotely, please merge locally, your changes will be found in .mod_{filename}.")
            os.system(f"cp {self.device_info_static.MY_STORAGE}/{filename} {self.device_info_static.MY_STORAGE}/.mod_{filename}")
            return False
