"""
Server for routing messages, setting up the application and creating the game matches.
"""

from socket import socket, AF_INET, SOCK_STREAM
import json
import time
import random
import threading

from auth_server import get_id

info = json.load(open("info.json"))
ADDR = info["Chat Server"]["ip"]
PORT = info["Chat Server"]["port"]
MAX_USERS = 20
MSG_SIZE = 2048


def generate_match_id():
    """
        :return: Create  ID for a match
    """
    data = json.load(open("database/open_matches.json"))
    while True:
        unique_id = str(random.randint(10, 1000))
        if unique_id not in data:
            return unique_id


class ChatServer:
    def __init__(self):
        # Setup chat server socket
        self.users = {}
        self.live_invites = {}
        self.matches = {}
        self.lobbies = {}

        try:
            self.server_socket = socket(AF_INET, SOCK_STREAM)
            self.server_socket.bind((ADDR, PORT))
            self.server_socket.listen(MAX_USERS)
            print("[Chat][+] Chat server is up.")

        except Exception as e:
            print(f"[Chat][CRITICAL] Chat server failed to go up ({e})")

    def run(self):

        while True:
            # Accept new connection and assign unique ID to users
            client, address = self.server_socket.accept()
            client_id = client.recv(MSG_SIZE).decode("utf8")  # Get his id in order to know who it is
            data = json.load(open("database/users_login_info.json"))
            new_user_info = {"socket": client, "username": data[client_id]["username"]}

            # Tell existing users about a new user
            self.notify_users(client_id,
                              json.dumps({
                                  "header": "user/new_user",  # What is being sent
                                  "id": client_id,  # ID
                                  "username": new_user_info["username"],  # USERNAME
                              }).encode("utf8"))

            # Tell new user about existing users for him to load home screen
            for user_id in self.users:
                if user_id != client_id:
                    user_info = self.users[user_id]
                    try:
                        client.send(json.dumps({
                            "header": "user/new_user",  # What is being sent
                            "id": user_id,
                            "username": user_info["username"],
                        }).encode("utf8"))
                        time.sleep(0.1)  # Pass some time before sending the next user
                    except OSError:
                        pass

            for lobby_id in self.lobbies:
                lobby_info = self.lobbies[lobby_id]
                try:
                    client.send(json.dumps(
                        {"user": lobby_info["user"],
                         "header": "lobbies/new_lobby",
                         "name": lobby_info["name"],
                         "max": lobby_info["max"],
                         "lobby_id": lobby_id,
                         "players": lobby_info["players"]

                         }).encode("utf8"))
                    time.sleep(0.1)  # Pass some time before sending the next user
                except OSError:
                    pass

            # Tell users some information for the UI
            client.send(json.dumps(
                {
                    "header": "utility/badges",
                    "lobbies": len(self.lobbies),
                    "users": len(self.users)

                }).encode("utf8"))
            time.sleep(0.1)
            client.send(
                json.dumps(
                    {
                        "header": "utility/users",
                        "users": self.send_users()

                    }).encode("utf8")
            )
            # Add new user to users list, effectively allowing it to receive messages from other users
            self.users[client_id] = new_user_info  # Example: "2783":{"socket":object, "username":Tim}

            # Start thread to receive messages from that client
            receive_thread = threading.Thread(target=self.handle_client, args=(client_id,), daemon=True).start()
            print(f"[Chat][+] New client connected (ID:{client_id})")

    def notify_users(self, avoid_id: str, data: bytes):
        """
        This function notifies online users new information about a user
        :param avoid_id: This is the ID of the user that we are updating about
        :param data: The new information about the user
        :return:
        """
        for user_id in self.users:
            if user_id != avoid_id:
                user_info = self.users[user_id]
                user_socket: socket = user_info["socket"]
                try:
                    user_socket.send(data)
                except OSError:
                    pass

    def handle_client(self, identifier: str):
        """
        This function handles the protocol and the client-server connection and between different users
        :param identifier: This specific thread is different from others because of the id
        :return:
        """
        client_info = self.users[identifier]  # Get the info about that client
        client: socket = client_info["socket"]  # Get the socket of the client
        username = client_info["username"]

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

            except Exception as e:
                print(f"[-] Error occurred with {username} (ID: {identifier}): {e}")
                continue

            header = msg_json["header"]

            print(f"[*] Received message from user: \"{username}\" with ID {identifier}: {header}")

            # Analyse data
            category = header.split('/')[0]

            if category == "chat":
                self.chat_system(client, identifier, msg_json)
            elif category == "lobbies":
                self.lobby_system(identifier, msg_json)
            elif category == "game":
                self.game_system(client, identifier, msg_json)
            elif category == "utility":
                if msg_json["body"] == "exit":
                    client.send("exit".encode('utf8'))
                    break
                if msg_json["body"] == "users":
                    self.send_users(client)
        # Tell other users about player leaving

        self.notify_users(identifier, json.dumps(
            {"id": identifier,
             "header": "user/leaving_user",
             "username": username}
        ).encode("utf8"))
        print(f"[-] User {username} with ID {identifier} has left the app...")
        del self.users[identifier]
        client.close()

    def chat_system(self, client: socket, identifier, msg_json):
        """
        This method helps to deal with any requests or posts related to chats
        :param client:
        :param identifier: The identifier of the user that requested or posted information
        :param msg_json: The content of the request/post
        :return:
        """
        sub_category = msg_json["header"].split('/')[1]
        if sub_category == "get_chat":
            chat_messages = []
            second_user_id = get_id(msg_json["username"])

            with open("database/chats.json") as jsonFile:
                chats = json.load(jsonFile)

            # NOTE: This part can be improved by adding usernames to each key of ids and then finding the chat by them.
            if f"{identifier}-{second_user_id}" in chats or f"{second_user_id}-{identifier}" in chats:
                try:
                    chat_messages = chats[f"{identifier}-{second_user_id}"]["messages"]
                except Exception as e:
                    chat_messages = chats[f"{second_user_id}-{identifier}"]["messages"]  # Get the list of messages
            else:
                chats[f"{identifier}-{second_user_id}"] = {"messages": []}  # Create a new chat log

                with open("database/chats.json", "w") as jsonFile:
                    json.dump(chats, jsonFile, indent=4, sort_keys=True)

                # json.dump(chats, open("database/chats.json", "w"), indent=4, sort_keys=True)
                chat_messages = [""]

            client.send(json.dumps({
                "header": "chat/get_chat",  # What is being sent
                "id": second_user_id,
                "messages": chat_messages,
            }).encode("utf8"))
        elif sub_category == "send_message":
            # When a user sends a message we need to do 2 things:
            # 1. Send the other user the message in order to update his screen
            # 2. Save that message in database for future use
            message = msg_json["message"]
            second_user_id = msg_json["id"]

            self.users[msg_json["id"]]["socket"].send(json.dumps({
                "header": "chat/receive_message",  # What is being sent
                "id": identifier,
                "message": message,
            }).encode("utf8")
                                                      )
            # Step 1 accomplished, now we save in database
            with open("database/chats.json") as jsonFile:
                chats = json.load(jsonFile)

            # Try for each option (as mentioned above, can be more effective in the future)
            try:
                chats[f"{identifier}-{second_user_id}"]["messages"].append({"text": message,
                                                                            "send_by_user": identifier
                                                                            })
            except Exception as e:
                chats[f"{second_user_id}-{identifier}"]["messages"].append({"text": message,
                                                                            "send_by_user": identifier
                                                                            })  # Get the list of messages

            with open("database/chats.json", "w") as jsonFile:
                json.dump(chats, jsonFile, indent=4, sort_keys=True)

            # Step 2 accomplished

    def lobby_system(self, identifier, msg_json):
        """
        This method helps to deal with any requests or posts related to lobbies
        :param identifier: The identifier of the user that requested or posted information
        :param msg_json: The content of the request/post
        :return:
        """
        sub_category = msg_json["header"].split('/')[1]
        if sub_category == "create_lobby":
            lobby_name = msg_json["name"]
            max_players = msg_json["max"]
            self.create_lobby(lobby_name, max_players, identifier)
        elif sub_category == "join_lobby":
            lobby_id = msg_json["id"]
            self.update_lobby_players(lobby_id, self.users[identifier]["username"], "join")
        elif sub_category == "leave_lobby":
            lobby_id = msg_json["id"]
            self.update_lobby_players(lobby_id, self.users[identifier]["username"], "leave")

    def game_system(self, client: socket, identifier: str, msg_json: dict):
        """
        Here we manage game invites, accepts, rejects and leading 2 players into a match from the app
        :param client:
        :param identifier:
        :param msg_json:
        :return:
        """
        sub_category = msg_json["header"].split('/')[1]
        if sub_category == "send_invite":
            # 1. Save invite
            # 2. Send the invite
            self.users[msg_json["id"]]["socket"].send(json.dumps({
                "header": "game/receive_invite",
                "id": identifier,
            }).encode("utf8"))

            second_id = msg_json["id"]
            self.live_invites[f"{identifier}-{second_id}"] = {
                f"{identifier}": "Ready",
                f"{second_id}": "Waiting"
            }
            print(f"[*] Invitation was created by {identifier}, waiting for {second_id}. ")

        elif sub_category == "accept_invite":
            # Change the the status of the player to Ready
            second_id = msg_json["id"]

            try:
                # Change the user who accepted to ready

                self.live_invites[f"{identifier}-{second_id}"][f"{identifier}"] = "Ready"
                if self.live_invites[f"{identifier}-{second_id}"][f"{second_id}"] == "Ready":
                    # If both players are ready, Notify *both* users to change to game server

                    self.start_game(client, identifier, second_id)
            except Exception:
                self.live_invites[f"{second_id}-{identifier}"][f"{identifier}"] = "Ready"
                if self.live_invites[f"{second_id}-{identifier}"][f"{second_id}"] == "Ready":
                    self.start_game(client, identifier, second_id)
        elif sub_category == "reject_invite":
            # The user that was invited, rejected the invite
            second_id = msg_json["id"]
            try:
                del self.live_invites[f"{identifier}-{second_id}"]
            except Exception:
                del self.live_invites[f"{second_id}-{identifier}"]

            self.users[second_id]["socket"].send(json.dumps({
                "header": "game/invite_rejected",
                "id": identifier,
            }).encode("utf8"))

    def start_game(self, client, identifier, second_id):
        """
        1. If both players are ready, Notify *both* users to change to game server
        2. Write in the matches.json
        :param client:
        :param identifier:
        :param second_id:
        :return:
        """

        # Save it in the json
        match_id = generate_match_id()
        with open("database/open_matches.json") as jsonFile:
            matches = json.load(jsonFile)

            matches[match_id] = {
                "users": [identifier, second_id],
                "players": 2,
                "spectators": 0
            }

        with open("database/open_matches.json", "w") as jsonFile:
            json.dump(matches, jsonFile, indent=4, sort_keys=True)
        self.matches[match_id] = [identifier, second_id]  # Give the pair an ID for their match

        # Now notify
        client.send(json.dumps({
            "header": "game/start_game",
            "id": identifier,  # Start a game with who?
            "match_id": match_id
        }).encode("utf8"))
        self.users[second_id]["socket"].send(json.dumps({
            "header": "game/start_game",
            "id": identifier,  # Start a game with who?
            "match_id": match_id
        }).encode("utf8"))

    def create_lobby(self, lobby_name, max_players, identifier):

        lobby_id = generate_match_id()
        with open("database/open_matches.json") as jsonFile:
            matches = json.load(jsonFile)

            matches[lobby_id] = {
                "users": {},
                "players": 2,
                "spectators": 0
            }

        with open("database/open_matches.json", "w") as jsonFile:
            json.dump(matches, jsonFile, indent=4, sort_keys=True)
        self.lobbies[lobby_id] = {"name": lobby_name,
                                  "id": lobby_id,
                                  "connected_players": 0,
                                  "max": max_players,
                                  "players": [],
                                  "user": self.users[identifier]["username"]}
        self.notify_new_lobby(lobby_id, identifier)

    def notify_new_lobby(self, lobby_id, identifier):
        self.notify_users("", json.dumps(
            {"user": self.lobbies[lobby_id]["user"],
             "header": "lobbies/new_lobby",
             "name": self.lobbies[lobby_id]["name"],
             "max": self.lobbies[lobby_id]["max"],
             "lobby_id": lobby_id,
             "players": self.lobbies[lobby_id]["players"]}
        ).encode("utf8"))

    def update_lobby_players(self, lobby_id, username, action):
        """

        :param lobby_id:
        :param username:
        :param action: Will the player join or leave
        :return:
        """
        # Add my username to the list of people who are in the lobby

        self.lobbies[lobby_id]["players"].append(username)
        self.notify_users("",
                          json.dumps(
                              {"username": username,
                               "header": f"lobbies/player_{action}",
                               "lobby_id": lobby_id
                               }
                          ).encode("utf8")
                          )

    def send_users(self):
        current_users = {}
        for user_id in self.users:
            user_info = self.users[user_id]
            current_users[user_info["username"]] = user_id
        print(f"Users: {current_users}")
        return current_users


if __name__ == "__main__":
    c = ChatServer()
    c.run()
