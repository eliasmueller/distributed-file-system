import ast
import os.path
import socket
import time

import device_info
import message_formatter as formatter
import util

BUFFER_SIZE = 4096


def transfer_file(ip,
                  port,
                  original_sender_id: int,
                  device_info_static: device_info.DeviceInfoStatic,
                  message_type: str,
                  vector_clock: dict,
                  file_location_name: str,
                  filename: str):
    tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket_sender.connect((ip, port))

    # here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    filepath = f"{device_info_static.MY_STORAGE}/{file_location_name}"
    if not os.path.isfile(filepath):
        message_type = "delete"
    tcp_socket_sender.send(str.encode(formatter.get_file_transfer_message(device_info_static,
                                                                          message_type,
                                                                          filename,
                                                                          vector_clock,
                                                                          original_sender_id)))
    print(f"Send file {filename} to {ip} on port {port}.")

    if message_type == "delete":
        tcp_socket_sender.close()
        return

    with open(filepath, "rb") as f:
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            print(bytes_read)
            if not bytes_read:
                break
            tcp_socket_sender.send(bytes_read)
        f.close()
    tcp_socket_sender.close()


def listen_for_file(listen_socket, device_info_static: device_info.DeviceInfoStatic) -> (str, dict, str, int, str, int):
    listen_socket.listen()
    conn_socket, addr = listen_socket.accept()
    print(f"Received tcp connection handshake from {addr}")
    received = conn_socket.recv(BUFFER_SIZE).decode().split("<SEPARATOR>")

    filename = received[1]
    vector_clock = ast.literal_eval(received[2])

    message_type = formatter.get_message_type(received[0])
    print(f"Receiving message with {message_type} file {filename} and vector clock {vector_clock}.")

    temp_version_number = 1
    vector_clock_str = util.vector_clock_to_path_string(vector_clock)
    temp_filename = f"tempversion_{vector_clock_str}_version{temp_version_number}_{filename}"
    filepath = f"{device_info_static.MY_STORAGE}/{temp_filename}"
    while os.path.exists(filepath):
        temp_version_number = temp_version_number + 1
        temp_filename = f"tempversion_{vector_clock_str}_version{temp_version_number}_{filename}"
        filepath = f"{device_info_static.MY_STORAGE}/{temp_filename}"

    if message_type != " file transfer delete":

        # make sure that the temp file exists + write beginning of file
        with open(filepath, "w") as f:
            if received[3] != "":  # possibly already the beginning of the file
                f.write(received[3])
                # TODO does not work in some unknown specific cases, especially on Linux

        with open(filepath, "wb") as f:
            while True:
                bytes_read = conn_socket.recv(BUFFER_SIZE)
                if not bytes_read:
                    break
                f.write(bytes_read)

    conn_socket.close()
    # b-deliver
    return filename, vector_clock, temp_filename, formatter.get_sender_id(
        received[0]), message_type, formatter.get_original_sender_id(received[0])


def transfer_entire_folder(device_info_static: device_info.DeviceInfoStatic,
                           device_info_dynamic: device_info.DeviceInfoDynamic, ip):
    folder_state = device_info_dynamic.PEER_file_state
    for f in folder_state.keys():
        if f.startswith(".") or f.startswith("~") or f.startswith("tempversion_") or f.startswith("lock_"):
            continue
        # We use the current clock at this will be discarded anyhow in this initial message exchange
        transfer_file(ip, 7772, device_info_static.PEER_ID, device_info_static, "file transfer modify",
                      device_info_dynamic.PEER_vector_clock, f, f)

