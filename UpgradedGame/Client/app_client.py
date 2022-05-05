import os
import socket
import json
from threading import Thread
from time import sleep

info = json.load(open("servers_info.json"))["Auth Server"]
ADDR = info["ip"]
PORT = info["port"]


class Client:
    def __init__(self):
        """
        A client class to abstract away socket functions and make communication with server.
        """

        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.addr = ADDR
            self.port = PORT
            self.id: str = ""
            self.connected = True
            self.recv_size = 2048
            self.client.connect((self.addr, int(self.port)))

        except socket.error as e:
            print(f"[-] Cannot establish connection with the server at ({self.addr}, {self.port})")

    def new_server(self, server):
        """
        Reconnect to a new server when completing a process with the current server
        :param server: Name of the server we are switching to
        :return:
        """

        print(f"[*] Switching server...")
        self.client.close()
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

        info = json.load(open("servers_info.json"))
        if server == "chat":
            self.addr = info["Chat Server"]["ip"]
            self.port = info["Chat Server"]["port"]

        elif server == "auth":
            self.addr = info["Auth Server"]["ip"],
            self.port = info["Auth Server"]["port"]

        try:
            self.client.connect((self.addr, int(self.port)))
            self.client.send(self.id.encode('utf8'))
            print(f"[+] Successfully connected to {server.upper()} server.")
            self.connected = True

        except Exception as e:
            print(f"[-] {server.upper()} server is not available. ({e})")

    def receive_updates(self):
        """
        This function starts running when connected to the chat server
        in order to receive real time updated from server without
        expecting them.
        :return: update_json: an update from the server
        """

        update = ""
        try:
            update = self.client.recv(self.recv_size)

        # Now we check for possible errors
        except ConnectionResetError as e:
            print(e)

        if not update or update == "":
            print(f"[-] Server at {self.addr}:{self.port} went offline.")

        update_decoded = update.decode("utf8")

        try:
            left_bracket_index = update_decoded.index("{")
            right_bracket_index = update_decoded.rindex("}") + 1
            update_decoded = update_decoded[left_bracket_index:right_bracket_index]

        except ValueError as e:
            print(e)

        update_json = ""
        try:
            update_json = json.loads(update_decoded)  # Load the received data into a dict
        except Exception as e:
            # Maybe we got en error because we have closed the app
            if update_json != "exit":
                print(update_decoded)
                print(f"[-] Error while receiving update from the server at ({self.addr}, {self.port}): {e}")

        # print(f"Received from server {pprint.pprint(update_json)}")
        return update_json

    def send(self, data):
        self.client.send(data.encode('UTF-8'))

    def settimeout(self, value):
        self.client.settimeout(value)

    def is_connected(self):
        while not self.connected:
            sleep(0.1)

    def receive_info(self):
        """
        The MainApp class runs this in order to receive real-time server updates
        :return:
        """
        msg = ""
        try:
            msg = self.client.recv(self.recv_size)
        except socket.error as e:
            print(f"[-] Error while receiving info from the server at ({self.addr}, {self.port}): {e}")

        if not msg:
            return None

        msg_decoded = msg.decode("utf8")

        left_bracket_index = msg_decoded.index("{")
        right_bracket_index = msg_decoded.index("}") + 1
        msg_decoded = msg_decoded[left_bracket_index:right_bracket_index]

        msg_json = json.loads(msg_decoded)

        return msg_json

    def auth(self, username, password):
        """
        Check if in database
        :param username:
        :param password:
        :return: boolean: If info is valid
        """
        self.client.send(json.dumps({
            "header": "login",  # What is being sent
            "username": username,
            "password": password,
        }).encode("utf8"))

        received = self.receive_info()
        if "id" in received:
            # Check if we were given an id
            self.id = received["id"]

        if "valid" in received and received["valid"]:
            return True
        return False

    def register(self, username, password):
        """
        :param username:
        :param password:
        :return: boolean: If all went good
        """
        self.client.send(json.dumps({
            "header": "register",  # What is being sent
            "username": username,
            "password": password,
        }).encode("utf8"))

        received = self.receive_info()
        if "id" in received:
            # Check if we were given an id
            self.id = received["id"]

        if "response" in received:
            return received["response"]

    def get_chat_data(self, username):
        """
        Every time we enter a chat with someone we need to receive all messages
        :param username: The user we are going to talk to
        :return:
        """
        self.client.send(json.dumps({
            "header": "chat/get_chat",  # What is being sent
            "username": username,

        }).encode("utf8"))

    def get_self_id(self):
        return self.id

    def send_chat_msg(self, msg: str, second_user_id: str):
        """
        This function is called when the user sends a message to another user
        :param second_user_id: The id of the user we are sending the message to
        :param msg: The content of the message
        :return:
        """
        self.client.send(json.dumps({
            "header": "chat/send_message",  # What is being sent
            "id": second_user_id,
            "message": msg
        }).encode("utf8"))

    def game_invite(self, user_id):
        """
        If user wants to invite someone to a game
        :param user_id: Who are we inviting
        :return:
        """
        self.client.send(json.dumps({
            "header": "game/send_invite",  # What is being sent
            "id": user_id,
        }).encode("utf8"))

    def accept_invite(self, user_id):
        self.client.send(json.dumps({
            "header": "game/accept_invite",  # What is being sent
            "id": user_id,
        }).encode("utf8"))

    def reject_invite(self, user_id):
        """
        Notify the user with the id that his invite was rejected
        :param user_id: Invite creator
        :return:
        """
        self.client.send(json.dumps({
            "header": "game/reject_invite",  # What is being sent
            "id": user_id,  # Who was rejected
        }).encode("utf8"))

    def start_game(self, creator, match_id, spectate=False):
        """
        Main Game Starter, new connection but it wont be part of this class
        as it requires full live data
        :param spectate:
        :param creator: The user who started the match
        :param match_id: The ID of the match
        :return:
        """
        if not spectate:
            print(f"[+] Entering {creator}'s match...")
            os.system(f"python game.py {match_id} {self.id}")
        else:
            print(f"[+] Spectating {creator}'s match...")
            os.system(f"python game.py {match_id} -1")

    def create_lobby(self, lobby_name: str, lobby_max_players: str):
        """
        Requesting server to create a lobby for us with a maximum number
        of players
        :param lobby_name:
        :param lobby_max_players:
        :return:
        """
        self.client.send(json.dumps({
            "header": "lobbies/create_lobby",  # What is being sent
            "name": lobby_name,
            "max": lobby_max_players
        }).encode("utf8"))

    def join_lobby(self, lobby_id: str):
        """
            This function is important because we need to update the lobby info for other users
            :param lobby_id: The lobby we are joining to
            :return:
        """
        self.client.send(json.dumps({
            "header": "lobbies/join_lobby",  # What is being sent
            "id": lobby_id,
        }).encode("utf8"))

    def disconnect(self):
        self.client.send(json.dumps({
            "header": "utility",  # What is being sent
            "body": "exit"
        }).encode("utf8"))

    def get_users(self):
        self.client.send(json.dumps({
            "header": "utility",  # What is being sent
            "body": "users "
        }).encode("utf8"))
