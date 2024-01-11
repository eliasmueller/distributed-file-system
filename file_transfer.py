import socket

import deviceInfo

buffer_size = 4096
tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def transfer_file(ip, port, device_info_static: deviceInfo.DeviceInfoStatic, filename: str):
    tcp_socket_sender.connect((ip, port))
    # TODO here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    vector_clock = {"123": 0, "234": 1}  # TODO only a demo implementation

    tcp_socket_sender.send(str.encode(f"{filename}<SEPARATOR>{vector_clock}"))
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
    filename, vector_clock = conn_socket.recv(buffer_size).decode().split("<SEPARATOR>")
    print(f"Receiving message with file {filename} and vector clock {vector_clock}.")
    # TODO here we must check if we actually can deliver the message or if we need to hold the changes back in the queue

    if vector_clock[123] == 0 & vector_clock[234] == 1:  # TODO Only a demo the proper check of course would iterate through all keys of the vector clock and compare to own
        filepath = f"{device_info_static.MY_STORAGE}/{filename}"
        with open(filepath, "wb") as f:
            while True:
                bytes_read = conn_socket.recv(buffer_size)
                if not bytes_read:
                    break
                f.write(bytes_read)
        conn_socket.close()
    else:
        print("Holding back message in hold back queue")
        # TODO add message to hold back queue and ensure other messages are incoming first
