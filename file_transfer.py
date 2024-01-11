import socket
import ast
import deviceInfo

buffer_size = 4096
tcp_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def transfer_file(ip, port, device_info_static: deviceInfo.DeviceInfoStatic, filename: str):
    tcp_socket_sender.connect((ip, port))
    # TODO here we can piggyback the information on the ordered reliable multicast (i.e. the vector clocks)
    vector_clock = {"123": 0, "234": 1}  # TODO only a demo implementation

    tcp_socket_sender.send(str.encode(f"{filename}<SEPARATOR>{vector_clock}<SEPARATOR>"))
    print(f"Send file {filename} to {ip}.")

    filepath = f"{device_info_static.MY_STORAGE}/{filename}"
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

    filename = received[0]
    vector_clock = ast.literal_eval(received[1])

    print(f"Receiving message with file {filename} and vector clock {vector_clock}.")

    # TODO here we must check if we actually can deliver the message or if we need to hold the changes back in the queue
    if vector_clock["123"] == 0 and vector_clock["234"] == 1:  # TODO Only a demo the proper check of course would iterate through all keys of the vector clock and compare to own
        filepath = f"{device_info_static.MY_STORAGE}/{filename}"
        with open(filepath, "wb") as f:
            if received[2] != "":  # possibly already the beginning of the file
                f.write(received[2])
            while True:
                bytes_read = conn_socket.recv(buffer_size)
                if not bytes_read:
                    break
                f.write(bytes_read)
        conn_socket.close()
    else:
        print("Holding back message in hold back queue")
        # TODO add message to hold back queue and ensure other messages are incoming first
