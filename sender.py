import socket
import deviceInfo as deviceInfo

broadcast_socket_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
buffer_size = 1024

def basic_broadcast(ip, port, message: str):
    # Send message on broadcast address
    broadcast_socket_sender.sendto(str.encode(message), (ip, port))
    #print(f"broadcasted {ip}, {port}: {message}")

def listen_for_answer(timeout_seconds: int) -> str:
    broadcast_socket_sender.settimeout(timeout_seconds)
    while True:
        try:
            data, addr = broadcast_socket_sender.recvfrom(buffer_size)
        except socket.timeout:
            return None
        if data:
            return data.decode()


