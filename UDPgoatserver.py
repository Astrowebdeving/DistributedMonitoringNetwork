from socket import *
import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
import threading
host = "0.0.0.0"
port = 7992
max_buf = 1024
name = subprocess.check_output("""ip=$(hostname -I | awk '{print $1}')
                                  cat /etc/hosts | grep $ip | awk '{print $2}'""", shell=True, text=True).strip()
corebase = subprocess.check_output("nproc", shell=True, text=True).strip()
MAX_WORKERS = int(corebase) * 2
EOT = "__END_OF_TRANSMISSION__"  # Regular string

def handle_client(sock, addr, initial_data):
    try:
        filename = initial_data.strip().decode('utf-8')
        print(f"Received file request from {addr}: {filename}")

        transfer_sock = socket(AF_INET, SOCK_DGRAM)
        transfer_sock.bind((host, 0))

        new_port = transfer_sock.getsockname()[1]
        sock.sendto(str(new_port).encode('utf-8'), addr)

        handle_file_transfer(transfer_sock, filename, addr)

    except Exception as e:
        print(f"Exception occurred for client {addr}: {e}")

def handle_file_transfer(sock, filename, addr):
    received_packets = {}
    finalsum = 0

    try:
        while True:
            data, client_addr = sock.recvfrom(max_buf)
            if data.startswith(EOT.encode('utf-8')):
                _, finalsum_str = data.decode('utf-8').split('|')
                finalsum = int(finalsum_str)
                print(f"Received EOT: {finalsum} packets expected.")
                break

            identifier = data[:40].decode('utf-8').strip()
            seq_num = int(identifier.split('_')[0].replace("{UIDZ}", ""))
            packet_data = data[40:]

            if seq_num not in received_packets:
                received_packets[seq_num] = packet_data
                print(f"Received packet {seq_num} from {client_addr}")

    except Exception as e:
        print(f"Error during file transfer: {e}")

    # Check for missing packets
    missing_packets = {seq_num for seq_num in range(finalsum) if seq_num not in received_packets}

    if missing_packets:
        print(f"Missing packets detected: {missing_packets}")
        missing_str = ",".join(map(str, missing_packets))
        sock.sendto(f"MISSING:{missing_str}".encode('utf-8'), addr)

        # Wait for missing packets to be resent
        for seq_num in missing_packets:
            try:
                data, client_addr = sock.recvfrom(max_buf)
                identifier = data[:40].decode('utf-8').strip()
                received_seq_num = int(identifier.split('_')[0].replace("{UIDZ}", ""))
                if received_seq_num == seq_num:
                    received_packets[seq_num] = data[40:]
                    print(f"Received missing packet {seq_num} from {client_addr}")
                    sock.sendto(b'ACK', addr)
            except Exception as e:
                print(f"Error receiving missing packet {seq_num}: {e}")
    else:
        sock.sendto(f"{name} ACK".encode('utf-8'), addr)
        print("All packets received successfully.")

    # Write the data to file
    with open(filename, 'wb') as f:
        for seq_num in sorted(received_packets.keys()):
            f.write(received_packets[seq_num])

    subprocess.call(['tar', '-xzvf', filename])
    sock.close()

def handle_udp_check():
    check_sock = socket(AF_INET, SOCK_DGRAM)
    check_sock.bind((host, 8105))
    print(f"Host checking server listening on {host}:8105")

    try:
        while True:
            data, addr = check_sock.recvfrom(max_buf)
            message = data.decode()
            if message.startswith("CHECK"):
                print(f"Received host check request from {addr}")
                response = f"HOST:{name}"
                check_sock.sendto(response.encode(), addr)
    except Exception as e:
        print(f"Exception occurred in host checking server: {e}")
    finally:
        check_sock.close()

def main():
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Server listening on {host}:{port}...")

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    # Start UDP check server in a separate thread
    check_thread = threading.Thread(target=handle_udp_check)
    check_thread.daemon = True
    check_thread.start()

    try:
        while True:
            data, addr = sock.recvfrom(max_buf)
            if data.decode('utf-8') == 'heartbeat1':
                response = f"{name} ACK"
                sock.sendto(response.encode('utf-8'), addr)
            else:
                executor.submit(handle_client, sock, addr, data)

    except Exception as e:
        print(f"Exception occurred in main server loop: {e}")

    finally:
        sock.close()
        with open("cur_server.txt", "w") as file:
            file.write(host)
        print(f"Server state saved to cur_server.txt")

if __name__ == '__main__':
    main()
