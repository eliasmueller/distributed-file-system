import ast
import multiprocessing
import os
import shutil
import time
from functools import cmp_to_key
from multiprocessing.managers import DictProxy

import device_info
import file_transfer
import sender as b_send
import shared_dict_helper
import util
from shared_dict_helper import DictKey


class FolderMonitor:
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 device_info_dynamic: device_info.DeviceInfoDynamic,
                 require_queue: multiprocessing.Queue,
                 delivered_queue: multiprocessing.Queue,
                 shared_dict: DictProxy,
                 lock):
        self.device_info_static = device_info_static
        self.device_info_dynamic = device_info_dynamic
        self.require_queue = require_queue
        self.delivered_queue = delivered_queue
        self.shared_dict = shared_dict
        self.file_state = dict()
        self.is_running = True
        self.lock = lock
        self.sent_and_received_messages = []

        self.run()

    def run(self):
        try:
            while self.is_running:
                self.check_necessary_resends()
                self.check_folder_changes()
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def check_necessary_resends(self):
        # add externally added messages to the local representation
        while not self.delivered_queue.empty():
            message = self.delivered_queue.get()
            self.sent_and_received_messages.append(message)
            self.sent_and_received_messages = sorted(self.sent_and_received_messages,
                                                     key=cmp_to_key(util.compare_vector_clocks))

        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        if not self.require_queue.empty():
            (ip, sender_id, last_known_vector_clock) = self.require_queue.get()
            required_vector_clock = ast.literal_eval(last_known_vector_clock)

            if self.device_info_static.PEER_ID in required_vector_clock.keys():
                for (filename, message_vector_clock, temp_filename, sender_id, message_type,
                     original_sender_id) in self.sent_and_received_messages:
                    if self.vector_clock_condition(message_vector_clock,
                                                   self.device_info_dynamic.PEERS,
                                                   required_vector_clock):
                        print(f"received require for {required_vector_clock} from {sender_id} on {ip}, "
                              f"resending message with {message_vector_clock}.")
                        file_transfer.transfer_file(
                            ip, 7771, self.device_info_static.PEER_ID, self.device_info_static, message_type,
                            message_vector_clock, temp_filename, filename)
                        return
                print(f"received require for {required_vector_clock} from {sender_id} on {ip}, found no matching message.") 

    def check_folder_changes(self):
        assert self.device_info_dynamic is not None
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        self.file_state = self.device_info_dynamic.PEER_file_state
        current_state = util.get_folder_state(self.device_info_static.MY_STORAGE)

        # adding and modification is the same representation.
        deleted_files = [f for f in self.file_state 
                         if f not in current_state 
                         and not os.path.isdir(os.path.join(self.device_info_static.MY_STORAGE, f))]
        modified_files = [f for f in current_state 
                          if current_state[f] != self.file_state.get(f, 0) 
                          and not os.path.isdir(os.path.join(self.device_info_static.MY_STORAGE, f))]

        if modified_files:
            self.notify_all_peers_about_file_change("modify", modified_files)
        if deleted_files:
            self.notify_all_peers_about_file_change("delete", deleted_files)

        self.file_state = current_state
        self.device_info_dynamic.PEER_file_state = self.file_state
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state, self.file_state)

    def consistent_ordered_multicast_file_change(self, message_type, f):
        # this is the start of the sending process for an ordered multicast
        # increase own vector clock entry
        self.device_info_dynamic.get_update_from_shared_dict(self.shared_dict)
        self.device_info_dynamic.increase_vector_clock_entry(self.device_info_static.PEER_ID, 1)
        shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_vector_clock,
                                              self.device_info_dynamic.PEER_vector_clock)
        b_send.reliable_multicast(self.device_info_static, self.device_info_dynamic, message_type, f)

        # attaching copy of sent version in case other peer requests resend
        temp_filename = f".tempversion_sender_{file_transfer.vector_clock_to_path_string(self.device_info_dynamic.PEER_vector_clock)}_{f}"
        if message_type != "delete":
            shutil.copy(os.path.join(self.device_info_static.MY_STORAGE, f),
                        os.path.join(self.device_info_static.MY_STORAGE, temp_filename))

        self.sent_and_received_messages.append((f, self.device_info_dynamic.PEER_vector_clock, temp_filename,
                                                self.device_info_static.PEER_ID, message_type,
                                                self.device_info_static.PEER_ID))
        # TODO remove at some point

    def notify_all_peers_about_file_change(self, message_type, files):
        print(f"Change detected: {message_type}, {files}")
        for f in files:
            if f.startswith("."):  # Working files could often start with "." we do not want to send this.
                continue
            if f.startswith("tempversion_"):  # not deliver file changes start with "tempversion_"
                continue
            if f.startswith("lock_"):  # to lock a file another file with same name and the prefix lock_ is created.
                if message_type == "modify":
                    self.lock_file(f)
                elif message_type == "delete":
                    self.unlock_file(f.split("lock_")[1], discard=True)
                continue
            if self.file_is_locked(f):
                if not self.unlock_file(f, discard=False):
                    continue
            print(f"sending {f}")
            self.consistent_ordered_multicast_file_change(message_type, f)
            time.sleep(0.15)

    def file_is_locked(self, filename: str):
        return filename in self.device_info_dynamic.LOCKED_FILES.keys()

    def lock_file(self, filename: str):
        file = filename.split("lock_")[1]
        filepath = f"{self.device_info_static.MY_STORAGE}/{file}"
        if os.path.exists(filepath):
            print(f"Locking file {file} locally.")
            self.device_info_dynamic.LOCKED_FILES[file] = "none"
            shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.locked_files,
                                                  self.device_info_dynamic.LOCKED_FILES)
        else:
            os.remove(f"{self.device_info_static.MY_STORAGE}/{filename}")

    def unlock_file(self, filename: str, discard: bool) -> bool:
        if not discard:  # when the lock file is deleted we don't delete anything else
            filepath = f"{self.device_info_static.MY_STORAGE}/lock_{filename}"
            os.remove(filepath)
        # if there has been no remote change we simply continue
        if discard or self.device_info_dynamic.LOCKED_FILES[filename] != "remote":
            print(f"Unlocking file {filename} locally.")
            return_val = True
        else:  # remote and local changes -> has to be merged manually
            print(
                f"File has been edited remotely, please merge locally, your changes will be found in .mod_{filename}.")
            os.system(
                f"cp {self.device_info_static.MY_STORAGE}/{filename} {self.device_info_static.MY_STORAGE}/.mod_{filename}")
            return_val = False
        if filename in self.device_info_dynamic.LOCKED_FILES.keys():
            del self.device_info_dynamic.LOCKED_FILES[filename]
            self.device_info_dynamic.update_entire_shared_dict(self.shared_dict, self.lock)
        return return_val

    def vector_clock_condition(self, message_vector_clock, peers, required_vector_clock) -> bool:
        for id in peers:
            if util.get_or_default(message_vector_clock, id) != util.get_or_default(required_vector_clock, id) + 1:
                return False
            for peer in self.device_info_dynamic.PEERS:
                if peer == id:
                    continue
                if util.get_or_default(message_vector_clock, peer) > util.get_or_default(required_vector_clock, peer):
                    return False
            return True
