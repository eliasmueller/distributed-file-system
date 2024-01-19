import socket
import ast
import os.path

import deviceInfo
import message_formater as formater

buffer_size = 4096


def transfer_file(ip, port, device_info_static: deviceInfo.DeviceInfoStatic, message_type: str, vector_clock: dict, filename: str):
    tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket_sender.connect((ip, port))

    #here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
    if not os.path.isfile(filepath):
        message_type = "delete"
    tcp_socket_sender.send(str.encode(formater.get_file_transfer_message(device_info_static,message_type,filename,vector_clock)))
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


def listen_for_file(conn_socket, device_info_static: deviceInfo.DeviceInfoStatic):
    received = conn_socket.recv(buffer_size).decode().split("<SEPARATOR>")

    filename = received[1]
    vector_clock = ast.literal_eval(received[2])

    print(f"Receiving message with file {filename} and vector clock {vector_clock}.")
    message_type = formater.get_message_type(received[0])
    temp_filename = f"tempversion_{filename}"

    if message_type == "delete":
        conn_socket.close()
        return filename, vector_clock, temp_filename, formater.get_sender_id(received[0])

    filepath = f"{device_info_static.MY_STORAGE}/{temp_filename}"
    
    with open(filepath, "w+") as f:
        print("tempfile")

    with open(filepath, "wb") as f:
        print("---------------------------------a")
        if received[3] != "":  # possibly already the beginning of the file
            print("---------------------------------b")
            f.write(received[3]) # TODO this is not working properly yet
        while True:
            print("---------------------------------c")
            bytes_read = conn_socket.recv(buffer_size)
            print("---------------------------------d")
            if not bytes_read:
                print("---------------------------------e")
                break
            print("---------------------------------f")
            f.write(bytes_read)
            print("---------------------------------g")
    conn_socket.close()
    print("b-deliver")
    return filename, vector_clock, temp_filename, formater.get_sender_id(received[0])

