import os
import time
import subprocess

hostlist = ["manager", "worker1", "worker2"]
contentfiletest = subprocess.check_output(
    "ip=$(hostname -I | awk '{print $1}')\n cat /etc/hosts | grep $ip | awk '{print $2}'", 
    shell=True, text=True).strip()

# Configuration
file_to_monitor = f"/home/mpiuser/allinfile_{contentfiletest}.txt"
check_interval = 8
timeout_interval = 24

def get_current_server(file_path):
    try:
        result = subprocess.run(['cat', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            server_content = result.stdout.strip()
            return server_content
        else:
            print(f"Error reading the file: {result.stderr}")
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")
    except Exception as e:
        print(f"Exception error has occurred in server file reading: {e}")

def get_last_modified_time(file_path):
    try:
        return os.path.getmtime(file_path)
    except FileNotFoundError:
        return None

def main():
    host = get_current_server("curr_server.txt")
    if host in hostlist:
        index = hostlist.index(host)
    else:
        index = 0
        host = hostlist[0]

    program_to_call = ["python3", "startingclientUDP.py", f"{host}"]
    last_modified_time = get_last_modified_time(file_to_monitor)

    while True:
        time.sleep(check_interval)

        if contentfiletest == host:
            print("it is working:", contentfiletest)
            try:
                subprocess.run(program_to_call, check=True)
                print(f"Called program with starting host: {host}")
                current_time = time.time()
            except subprocess.CalledProcessError as e:
                print(f"Error calling program with starting host: {e}")
                current_time = time.time()

        elif get_last_modified_time(file_to_monitor) is None:
            print(f"File '{file_to_monitor}' not found.")
            continue
        # Check if the file has not been updated within the timeout interval
        elif get_last_modified_time(file_to_monitor) is not None and (time.time() - get_last_modified_time(file_to_monitor)) > timeout_interval:
            current_time = time.time()
            print(current_time - get_last_modified_time(file_to_monitor))
            # Change host to the next hostname in the hostlist
            index = (index + 1) % len(hostlist)
            host = hostlist[index]
            with open("curr_server.txt", "w") as file:
                file.write(host)
            print(f"Host changed to {host}")

            # Update the program_to_call to use the new host
            program_to_call[-1] = host

        elif get_last_modified_time(file_to_monitor)!= last_modified_time:
            last_modified_time = get_last_modified_time(file_to_monitor)

if __name__ == "__main__":
    main()
