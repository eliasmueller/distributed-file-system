import multiprocessing
import os
import socket
from multiprocessing.managers import DictProxy

import device_info
import file_transfer
import shared_dict_helper
import util
from shared_dict_helper import DictKey

BUFFER_SIZE = 4096


class FileInitListener(multiprocessing.Process):
    def __init__(self,
                 device_info_static: device_info.DeviceInfoStatic,
                 shared_dict: DictProxy,
                 lock):
        super(FileInitListener, self).__init__()
        self.device_info_static = device_info_static
        self.shared_dict = shared_dict
        self.isRunning = True
        self.lock = lock
        self.file_state = dict()
        self.port = 7772
        # Create a TCP socket
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.device_info_static.MY_IP, self.port))
        self.buffer_size = BUFFER_SIZE

    def run(self):
        print("Listening for initial folder structure from leader on port 7772")
        try:
            self.file_init_listener()
        finally:
            print("finished listening to initial folder structure")
            self.listen_socket.close()

    def file_init_listener(self):
        # TODO self destruct after 10s
        self.clean_up_old_temp_files()
        while self.isRunning:
            filename, vector_clock, temp_filename, sender_id, message_type, orig_sender_id = (
                file_transfer.listen_for_file(self.listen_socket, self.device_info_static))
            filepath_file = f"{self.device_info_static.MY_STORAGE}/{filename}"
            filepath_temp = f"{self.device_info_static.MY_STORAGE}/{temp_filename}"

            os.replace(filepath_temp, filepath_file)

            self.file_state.update({filename: os.path.getmtime(filepath_file)})
            shared_dict_helper.update_shared_dict(self.shared_dict, self.lock, DictKey.peer_file_state, self.file_state)

    def clean_up_old_temp_files(self):
        for f in util.get_folder_state(self.device_info_static.MY_STORAGE).keys():
            if f.startswith(".tempversion_") or f.startswith("tempversion_"):
                util.delete_file(f, self.device_info_static.MY_STORAGE)