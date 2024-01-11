import multiprocessing
import os
import time

import deviceInfo
import file_transfer
import util


class FolderMonitor:
    def __init__(self, device_info_static: deviceInfo.DeviceInfoStatic,
                 device_info_dynamic: deviceInfo.DeviceInfoDynamic, shared_queue: multiprocessing.Queue):
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.shared_queue = shared_queue
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
            self.notify_all_peers_about_file_change(list(set(added_files + deleted_files + modified_files)))

        self.file_state = current_state

    def run(self):
        try:
            while self.is_running:
                # TODO we need an observer pattern to detect this properly
                # self.update_from_queue()
                self.check_folder_changes()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # TODO this must be secured by ordered reliable multicast, maybe in another file
    def notify_all_peers_about_file_change(self, files):
        print(f"Change detected, {files}")
        for f in files:
            if not f.startswith("."):  # Working files could often start with "." we do not want to send this.
                print(f"sending {f}")
                for p in self.device_info_dynamic.PEERS:
                    if p != self.device_info_static.PEER_ID:
                        ip = self.device_info_dynamic.PEER_IP_DICT[p]
                        file_transfer.transfer_file(ip=ip, port=7771, device_info_static=self.device_info_static, filename=f)

    # def update_from_queue(self):
    #     if not self.shared_queue.empty():
    #         queue_message = util.consume(self.shared_queue)
    #         if isinstance(queue_message, deviceInfo.DeviceInfoDynamic):
    #             self.device_info_dynamic = queue_message
    #         # If not necessary for me, put back
    #         else:
    #             self.shared_queue.put(queue_message)
