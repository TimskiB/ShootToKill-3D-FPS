"""
Server for checking authentication of users and create users
"""

from socket import socket, AF_INET, SOCK_STREAM
import json
import time
import random
import threading

info = json.load(open("info.json"))
ADDR = info["Auth Server"]["ip"]
PORT = info["Auth Server"]["port"]
MAX_USERS = 20
MSG_SIZE = 2048


def generate_id():
    """
    :return: Create  ID for a user
    """
    data = json.load(open("database/users_login_info.json"))
    while True:
        unique_id = str(random.randint(10, 1000))
        if unique_id not in data:
            return unique_id


def login_process(msg_json):
    """
    This function check if the login info that was entered is valid
    and in the database of the server
    :param msg_json: The login info
    :return:
    """
    username = msg_json["username"]
    password = msg_json["password"]
    data = json.load(open("database/users_login_info.json"))

    for user in data.values():
        if user["username"] == username:  # Does user exist
            if user["password"] == password:  # Do the passwords match
                return True

    return False


def register_process(msg_json, user_id):
    """

    :param msg_json:
    :param user_id: string:
    :return:
    """
    try:
        username = msg_json["username"]
        if check_username_option(username):
            data = json.load(open("database/users_login_info.json"))
            data[user_id] = {"username": username, "password": msg_json["password"]}
            json.dump(data, open("database/users_login_info.json", "w"), indent=4, sort_keys=True)
            return "valid"
        else:
            return f"taken"
    except Exception as e:
        print(f"[Auth][-] Can't save entry. ({e})")
        return "error"


def check_username_option(username):
    """
    Check if a username is available and not taken.
    :param username: Check For this username
    :return:
    """
    data = json.load(open("database/users_login_info.json"))
    for user in data.values():
        if user["username"] == username:
            return False
    return True


def get_id(username: str):
    """
    Get the ID of the received username
    :param username: Receive username
    :return:
    """
    data = json.load(open("database/users_login_info.json"))

    for user_id, user_data in data.items():
        if user_data["username"] == username:
            return user_id


class AuthServer:
    def __init__(self):
        # Setup server socket
        try:
            self.server_socket = socket(AF_INET, SOCK_STREAM)
            self.server_socket.bind((ADDR, PORT))
            self.server_socket.listen(MAX_USERS)
            print("[Auth][+] Authentication server is up.")
        except Exception as e:
            print(f"[Auth][CRITICAL] Authentication server failed to go up ({e})")

    def run(self):
        while True:
            # Accept new connection and receive login
            client, address = self.server_socket.accept()
            print(f"[Auth][+] New client connected ({address})")
            threading.Thread(target=self.handle_client, args=(client, address,)).start()

    def handle_client(self, client, address):
        while True:
            try:
                received_data = client.recv(MSG_SIZE)

            # Now we check for possible errors
            except ConnectionResetError:
                break

            if not received_data:
                break

            msg_decoded = received_data.decode("utf8")

            try:
                left_bracket_index = msg_decoded.index("{")
                right_bracket_index = msg_decoded.index("}") + 1
                msg_decoded = msg_decoded[left_bracket_index:right_bracket_index]

            except ValueError:
                continue

            try:
                msg_json = json.loads(msg_decoded)  # Load the received data into a dict
                header = msg_json["header"]  # login/register
                print(f"[Auth][*] {address} requested {header}")
            except Exception as e:
                print(f"[Auth][-] Error occurred with {address}: {e}")
                continue

            if header == "login":

                client.send(json.dumps({
                    "header": "login",  # What is being sent
                    "valid": login_process(msg_json),
                    "id": get_id(msg_json["username"])
                }).encode("utf8"))


            else:
                registered_id = generate_id()
                client.send(json.dumps({
                    "header": "register",  # What is being sent
                    "response": register_process(msg_json, registered_id),
                    "id": registered_id
                }).encode("utf8"))


if __name__ == "__main__":
    a = AuthServer()
    a.run()
