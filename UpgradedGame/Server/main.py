import json
import os
import socket
import subprocess
from threading import Thread

from pyngrok import ngrok

from chat_server import ChatServer
from auth_server import AuthServer
# import ray
from multiprocessing import Process
from game_server import GameServer


def port_forward():
    os.system("ngrok.exe start --all")


def update_addresses(option):
    """
    New function that defines addresses of every server
    whether it is from ngrok or local addresses
    :param option:
    :return:
    """
    local_options = ["2", "local", "l", "Local", "L"]

    if option in local_options:
        # Set to local hosts
        with open("info.json") as info:
            data = json.load(info)
        print(f"[MAIN] Starting up all servers on this machine: {socket.gethostbyname(socket.gethostname())}")
        ports = [12350, 12351, 12352]
        port_index = 0

        for server in data:
            # Update ip addresses
            data[server]["ip"] = socket.gethostbyname(socket.gethostname())
            data[server]["port"] = ports[port_index]
            port_index += 1

        with open("info.json", "w") as info:
            json.dump(data, info, indent=4, sort_keys=True)
        Thread(target=addresses_server, args=(True,)).start()
    else:
        # Set to ngrok hosts
        with open("info.json") as info:
            data = json.load(info)
        for server in data:
            data[server]["ip"] = "localhost"
        with open("info.json", "w") as info:
            json.dump(data, info, indent=4, sort_keys=True)

        with open("online_info.json") as info:
            data = json.load(info)
        server_index = 1
        print("[*] Enter servers info from your ngrok window (URL:PORT):")
        for server in data:
            input_data = input(f"\t[?] Enter server {server_index} info: ")
            data[server]["ip"] = input_data.split(':')[0]
            data[server]["port"] = input_data.split(':')[1]
            server_index += 1
        with open("online_info.json", "w") as info:
            json.dump(data, info, indent=4, sort_keys=True)
        print(f"[MAIN] Starting up all servers on ngrok: {socket.gethostbyname(socket.gethostname())}")
        Thread(target=addresses_server, args=(False,)).start()  # Run a public server that sends the addresses


def send_addresses(client, addr, local):
    if local:
        with open("info.json") as info:
            data = json.load(info)
        client.send(
            json.dumps(data).encode('utf8')
        )
    else:
        with open("online_info.json") as info:
            data = json.load(info)
        client.send(
            json.dumps(data).encode('utf8')
        )
    print(f"[*] Sent addresses to {addr}")


def addresses_server(local):
    host = "localhost"
    port = 12344
    # Create a TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind a local socket to the port
    server_address = (host, port)
    server.bind(server_address)
    server.listen(2)

    if local:
        # One ngrok tunnel for the address server
        public_url = ngrok.connect(12344, "tcp").public_url
        url, url_port = public_url.strip("tcp://").split(":")
        print(f"\n[*] When connecting clients enter:\n\tHOST: {url}\n\tPORT: {url_port}")
    else:
        public_host = input(f"\t[?] Enter address server info: ")
        print(
            f"\n[*] When connecting clients enter:\n\tHOST: {public_host.split(':')[0]}\n\tPORT: {public_host.split(':')[1]}")
    while True:
        try:
            client, address = server.accept()
            Thread(target=send_addresses, args=(client, address, local,)).start()

        except KeyboardInterrupt:
            print("[-] Shutting down the address server...")
            break
    server.close()


def Main():
    # Update the address of each server to local or online addresses
    # update_addresses(input(
    #     "[?] Running online/local:\n\t[1] Online\n\t[2] Local\n "))

    Thread(target=run_a).start()
    Thread(target=run_b).start()
    Thread(target=run_c).start()


def run_a():
    os.system(f"python auth_server.py")


def run_b():
    os.system(f"python chat_server.py")


def run_c():
    os.system(f"python game_server.py")


if __name__ == "__main__":
    Main()
