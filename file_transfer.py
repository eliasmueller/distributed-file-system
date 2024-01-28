import socket
import ast
import os.path

import deviceInfo
import message_formater as formater

buffer_size = 4096


def transfer_file(ip,
                  port,
                  original_sender_id: int,
                  device_info_static: deviceInfo.DeviceInfoStatic,
                  message_type: str,
                  vector_clock: dict,
                  file_location_name: str,
                  filename: str):
    tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket_sender.connect((ip, port))

    #here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    filepath = f"{device_info_static.MY_STORAGE}/{file_location_name}"
    if not os.path.isfile(filepath):
        message_type = "delete"
    tcp_socket_sender.send(str.encode(formater.get_file_transfer_message(device_info_static,message_type,filename,vector_clock,original_sender_id)))
    print(f"Send file {filename} to {ip}.")

    if message_type == "delete":
        tcp_socket_sender.close()
        return
    
    with open(filepath, "rb") as f:
        while True:
            bytes_read = f.read(buffer_size)
            print(bytes_read)
            if not bytes_read:
                break
            tcp_socket_sender.send(bytes_read)
        f.close()
    tcp_socket_sender.close()

def vector_clock_to_path_string(vector_clock: dict):
    vc_str = str(vector_clock)
    vc_str = vc_str.replace(':','_')
    vc_str = vc_str.replace('(','_')
    vc_str = vc_str.replace('{','_')
    vc_str = vc_str.replace(')','_')
    vc_str = vc_str.replace('}','_')
    vc_str = vc_str.replace(',','_')
    vc_str = vc_str.replace(' ','')
    return vc_str

def listen_for_file(listen_socket, device_info_static: deviceInfo.DeviceInfoStatic) -> (str, dict, str, int, str):
    listen_socket.listen()
    conn_socket, addr = listen_socket.accept()
    print(f"Received tcp connection handshake from {addr}")
    received = conn_socket.recv(buffer_size).decode().split("<SEPARATOR>")

    filename = received[1]
    vector_clock = ast.literal_eval(received[2])

    message_type = formater.get_message_type(received[0])
    print(f"Receiving message with {message_type} file {filename} and vector clock {vector_clock}.")
    temp_filename = f"tempversion_{vector_clock_to_path_string(vector_clock)}_{filename}"

    if message_type != " file transfer delete":

        filepath = f"{device_info_static.MY_STORAGE}/{temp_filename}"
        #print(f"{filepath}")

        #make sure that the temp file exists + write beginning of file
        with open(filepath, "w") as f:
            if received[3] != "":  # possibly already the beginning of the file
                f.write(received[3])
                #TODO dose not work in some unknown specific cases

        with open(filepath, "wb") as f:
            while True:
                bytes_read = conn_socket.recv(buffer_size)
                if not bytes_read:
                    break
                f.write(bytes_read)

    conn_socket.close()
    #b-deliver
    return filename, vector_clock, temp_filename, formater.get_sender_id(received[0]), message_type, formater.get_original_sender_id(received[0])

