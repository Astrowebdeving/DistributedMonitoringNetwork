import socket
import sys
machinelist = ["manager", "worker1", "worker2"]

current_host = sys.argv[1]
def udp_client(server):
    UDP_IP = server 
    UDP_PORT = 8104
    MESSAGE = f"START_PROCESS:{current_host}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(MESSAGE.encode(), (UDP_IP, UDP_PORT))
        print(f"Sent message to server: {MESSAGE}")

        data, server = sock.recvfrom(128)
        print(f"Received acknowledgment from server: {data.decode()}")

    finally:
        sock.close()

if __name__ == "__main__":
    for client in machinelist:
        print(client, "is being sent to")
        udp_client(client)
