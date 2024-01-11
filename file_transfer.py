import socket

import deviceInfo

buffer_size = 4096
tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def transfer_file(ip, port, device_info_static: deviceInfo.DeviceInfoStatic, filename: str):
    tcp_socket_sender.connect((ip, port))
    tcp_socket_sender.send(str.encode(f"{filename}"))
    print(f"Send file {filename} to {ip}.")

    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
    with open(filepath, "rb") as f:
        while True:
            bytes_read = f.read(buffer_size)
            print(bytes_read)
            if not bytes_read:
                break
            tcp_socket_sender.sendall(bytes_read)
    tcp_socket_sender.close()


def listen_for_file(conn_socket, device_info_static: deviceInfo.DeviceInfoStatic):

    filename = conn_socket.recv(buffer_size).decode()
    print(f"Receiving file {filename}.")

    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
    with open(filepath, "wb") as f:
        while True:
            bytes_read = conn_socket.recv(buffer_size)
            if not bytes_read:
                break
            f.write(bytes_read)
    conn_socket.close()
