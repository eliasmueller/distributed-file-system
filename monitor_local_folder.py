import multiprocessing
import os
import time

import deviceInfo
import file_transfer
import sender as bSend

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
        self.file_state = self.get_folder_state()
        self.is_running = True

        self.run()

    def get_folder_state(self):
        return {f: os.path.getmtime(os.path.join(self.device_info_static.MY_STORAGE, f)) for f in
                os.listdir(self.device_info_static.MY_STORAGE)}

    def check_folder_changes(self):
        # TODO supervise that changes triggered by remote updates are ignored
        current_state = self.get_folder_state()

        added_files = [f for f in current_state if f not in self.file_state]
        deleted_files = [f for f in self.file_state if f not in current_state]
        modified_files = [f for f in current_state if current_state[f] != self.file_state.get(f, 0)]

        if added_files or deleted_files or modified_files:
            # TODO deleted files obviously cannot be sent
            self.notify_all_peers_about_file_change(list(set(added_files + deleted_files + modified_files)))

        self.file_state = current_state

    def run(self):
        try:
            while self.is_running:
                self.update_from_queue()
                self.check_folder_changes()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def consistent_ordered_multicast_file_change(self, f): 
        #increase own vector clock entry
        self.device_info_dynamic.PEER_vector_clock.increase_vector_clock_entry(self.device_info_static.PEER_ID, 1)
        # TODO instead of (iterating over peers tcp) B multicast use (tcp) R multicast
        bSend.basic_multicast(self.device_info_static, self.device_info_dynamic, f)

    def notify_all_peers_about_file_change(self, files):
        print(f"Change detected, {files}")
        for f in files:
            if not f.startswith("."):  # Working files could often start with "." we do not want to send this.
                print(f"sending {f}")
                self.ordered_multicast_file_change(f)
                
    def update_from_queue(self):
        self.device_info_dynamic = self.shared_dict.get("device_info_dynamic")
