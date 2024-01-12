import socket
import deviceInfo as deviceInfo

#self operating system
#w = windows, m = mac OS, l = linux
OPERATING_SYSTEM = "w"

broadcast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if OPERATING_SYSTEM != "w":
    broadcast_socket_sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
buffer_size = 1024


def basic_broadcast(ip, port, message: str):
    # Send message on broadcast address
    broadcast_socket_sender.sendto(str.encode(message), (ip, port))
    # print(f"broadcasted {ip}, {port}: {message}")


def listen_for_answer(timeout_seconds: int) -> str:
    broadcast_socket_sender.settimeout(timeout_seconds)
    while True:
        try:
            data, addr = broadcast_socket_sender.recvfrom(buffer_size)
        except socket.timeout:
            return None
        if data:
            return data.decode()
