from socket import *
import subprocess
import os
import random
import threading
import time

# Define the list of hosts
hostlist = ["manager", "worker1", "worker2"]

# Read host from curr_server.txt
with open("curr_server.txt", "r") as file:
    curr_server = file.readline().strip()

# Ensure the curr_server matches an entry in hostlist
if curr_server in hostlist:
    index = hostlist.index(curr_server)
    host = hostlist[index]
else:
    raise ValueError(f"The server name '{curr_server}' is not in the hostlist: {hostlist}")

# Parameters
port = 7992
max_buf = 1024
EOT = "__END_OF_TRANSMISSION__"  # Regular string
ACK_TIMEOUT = 2  # Timeout for ACK in seconds

# Retrieve the machine's name
name = subprocess.check_output("""ip=$(hostname -I | awk '{print $1}')
                                  cat /etc/hosts | grep $ip | awk '{print $2}'""", shell=True, text=True).strip()

# Retrieve content for the filename
contentfiletest = subprocess.check_output("ip=$(hostname -I | awk '{print $1}')\n cat /etc/hosts | grep $ip | awk '{print $2}'", shell=True, text=True).strip()

def generate_identifier(seq_num, name, prefix_suffix="{UIDZ}", length=40):
    seq_num_str = str(seq_num)
    identifier = f"{prefix_suffix}{seq_num_str}_{name}{prefix_suffix}"
    return identifier.ljust(length)  # Ensure the identifier fits the required length and pad if necessary

def send(file_name):
    s = socket(AF_INET, SOCK_DGRAM)
    s.settimeout(ACK_TIMEOUT)
    addr = (host, port)
    subprocess.call(['tar', '-czvf', file_name[:-3]+"tar.gz", file_name])
    file_name = file_name[:-3]+"tar.gz"

    s.sendto(file_name.encode('utf-8'), addr)

    data, server_addr = s.recvfrom(max_buf)
    new_port = int(data.decode('utf-8'))
    new_addr = (host, new_port)

    with open(file_name, "rb") as f:
        seq_num = 0
        data = f.read(max_buf - 40)  # Adjusted for new identifier length
        total_packets = 0
        packets = {}
        while data:
            identifier = generate_identifier(seq_num, name)
            packet = identifier.encode('utf-8') + data
            packets[seq_num] = packet
            s.sendto(packet, new_addr)
            seq_num += 1
            total_packets += 1
            data = f.read(max_buf - 40)
    
    try:
        eot_message = f"{EOT}|{total_packets}"
        s.sendto(eot_message.encode('utf-8'), new_addr)

        # Wait for response indicating any missing packets
        missing_packets = []
        try:
            response, _ = s.recvfrom(max_buf)
            response = response.decode('utf-8')
            if response.startswith("MISSING"):
                missing_packets = list(map(int, response.split(":")[1].split(",")))
        except timeout:
            print("No response regarding missing packets")

        # Resend any missing packets
        for seq_num in missing_packets:
            if seq_num in packets:
                print(f"Resending missing packet {seq_num}")
                s.sendto(packets[seq_num], new_addr)
                response, _ = s.recvfrom(max_buf)
                print(f"Received: {response.decode('utf-8')}")

        s.close()
    except timeout:
        print(f"No response from {host} during EOT")
        return False

def check_hosts():
    check_sock = socket(AF_INET, SOCK_DGRAM)
    check_sock.settimeout(2)  # Timeout for checking
    addr = (host, 8105)  # Same port as the UDP check server
    while True:
        if random.random() < 0.10:
            for i in range(len(hostlist)):
                test_host = hostlist[i]
                try:
                    message = "CHECK"
                    check_sock.sendto(message.encode(), (test_host, 8105))
                    response, _ = check_sock.recvfrom(max_buf)
                    if response.decode().startswith("HOST:"):
                        host_name = response.decode().split(":")[1]
                        if host_name in hostlist and host_name != host:
                            print(f"{test_host} is online. Switching host.")
                            global host
                            host = test_host
                            with open("curr_server.txt", "w") as file:
                                file.write(test_host)
                            break
                except Exception as e:
                    print(f"{test_host} is offline or unreachable: {e}")
        time.sleep(5)  # Check every 5 seconds

# Send files
filelist = [f"updatedmemoryram_{contentfiletest}.csv", f"updatedstorage_{contentfiletest}.csv", f"updatedstorage3_{contentfiletest}.csv", f"allinfile_{contentfiletest}.txt"]

for file_name in filelist:
    send(file_name)

# Start host check thread
check_thread = threading.Thread(target=check_hosts)
check_thread.daemon = True
check_thread.start()

# Keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting the program.")
