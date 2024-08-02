import socket
import subprocess
import os
host = "manager"
selfserver = subprocess.check_output("ip=$(hostname -I | awk '{print $1}')\n cat /etc/hosts | grep $ip | awk '{print $2}'", shell=True, text=True).strip()
def udp_server():
    UDP_IP = "0.0.0.0"  
    UDP_PORT = 8104
    BUFFER_SIZE = 128

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Server listening on port {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)  
        message = data.decode()
        print(f"Received message from {addr}: {message}")

        if message[:13] == "START_PROCESS":
            host = str(message[14:])
            print("We have received a message saying", host)
            with open("curr_server.txt", "w") as file:
                file.write(host)
            if host == selfserver:
                subprocess.Popen(['python3', 'newtest.py'])
            else:
                subprocess.Popen(['python3', 'UDPgoatclient.py'])
            ack_message = f"Process started on {selfserver}"
            sock.sendto(ack_message.encode(), addr)
        elif message[:13] != "START_PROCESS": 
            print("Corrupted Connection")

if __name__ == "__main__":
    udp_server()
