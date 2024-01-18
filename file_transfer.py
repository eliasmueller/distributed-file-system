import socket
import ast

import deviceInfo
import messageFormater as formater

buffer_size = 4096


def transfer_file(ip, port, device_info_static: deviceInfo.DeviceInfoStatic, vector_clock: dict, filename: str):
    tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket_sender.connect((ip, port))

    #here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    tcp_socket_sender.send(str.encode(formater.get_file_transfer_message(device_info_static,filename,vector_clock)))
    print(f"Send file {filename} to {ip}.")

    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
    #TODO delite file causes error in windof
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

    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
    with open(filepath, "wb") as f:
        if received[3] != "":  # possibly already the beginning of the file
            f.write(received[3]) # TODO this is not working properly yet
        while True:
            bytes_read = conn_socket.recv(buffer_size)
            if not bytes_read:
                break
            #f.write(bytes_read)# TODO this is curently to early maybe in a temp file
    conn_socket.close()

    return filename, vector_clock, temp_filename, formater.get_sender_id(received[0])

