"""
Server script for hosting games
"""

import socket
import json
import time
import random
import threading

info = json.load(open("info.json"))
ADDR = info["Game Server"]["ip"]
PORT = info["Game Server"]["port"]
MAX_PLAYERS = 20
MSG_SIZE = 2048


def get_username_by_id(identifier):
    data = json.load(open("database/users_login_info.json"))
    return data[identifier]["username"]


def receive_from_client(client, address):
    """
    The function does the recv method with a client and puts the data
    in a dict
    :param client: socket object
    :param address: The address of the client
    :return:
    """
    try:
        msg = client.recv(MSG_SIZE)

    # Catch errors
    except ConnectionResetError as e:
        print(f"[-] Error with {address}: {e}")
        return None

    if not msg:
        return None

    msg_decoded = msg.decode("utf8")

    try:
        left_bracket_index = msg_decoded.index("{")
        right_bracket_index = msg_decoded.index("}") + 1
        msg_decoded = msg_decoded[left_bracket_index:right_bracket_index]
    except ValueError as e:
        print(f"[-] Error with {address}: {e}")
        return None

    try:
        msg_json = json.loads(msg_decoded)
        return msg_json
    except Exception as e:
        print(f"[-] Error with {address}: {e}")
        return None


class GameServer:
    def __init__(self):
        # Set up server socket
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind((ADDR, PORT))
            self.server.listen(MAX_PLAYERS)
            print("[Game][+] Game server is up.")

        except Exception as e:
            print(f"[Game][CRITICAL] Game server failed to go up ({e})")
        self.matches = {}

        """This is an example of how the variable looks"""
        #
        # matches = {
        #     "match_id": {
        #         "players": {"id":
        #                         {
        #                           "socket": object,
        #                           "username": username,
        #                           "position": (0, 1, 0),
        #                           "rotation": 0,
        #                           "health": 100
        #                          },
        #                     "id":{
        #                           "socket": object,
        #                           "username": username,
        #                           "position": (0, 1, 0),
        #                           "rotation": 0,
        #                           "health": 100
        #                          },
        #                     }
        #           "spectators": []
        #     }
        #
        # }

    def main(self):

        while True:
            # Accept new connection and assign unique ID
            client, address = self.server.accept()
            data = receive_from_client(client, address)
            identifier = data["id"]
            match_id = data["match_id"]
            if identifier == "-1":
                # Spectator Mode
                self.spectator(match_id, client)
            else:
                new_player_info = {"socket": client,
                                   "username": get_username_by_id(identifier),
                                   "position": (0, 10, 0),
                                   "rotation": 0,
                                   "health": 100
                                   }

                # Tell existing players in that match about new player
                if match_id in self.matches:
                    for player_id in self.matches[match_id]["players"]:
                        if player_id != identifier:
                            player_info = self.matches[match_id]["players"][player_id]
                            player_conn: socket.socket = player_info["socket"]
                            try:
                                player_conn.send(json.dumps({
                                    "id": identifier,
                                    "object": "player",
                                    "username": new_player_info["username"],
                                    "position": new_player_info["position"],
                                    "health": new_player_info["health"],
                                    "joined": True,
                                    "left": False
                                }).encode("utf8"))
                            except OSError:
                                pass

                else:
                    # Create new record for this match
                    self.matches[match_id] = {"players": {}, "spectators": []}

                # Tell the same to spectators
                for spectator_socket in self.matches[match_id]["spectators"]:
                    try:
                        spectator_socket.send(
                            json.dumps({
                                "id": identifier,
                                "object": "player",
                                "username": new_player_info["username"],
                                "position": new_player_info["position"],
                                "health": new_player_info["health"],
                                "joined": True,
                                "left": False
                            }).encode("utf8")
                        )
                    except OSError:
                        pass

                # Tell new player about existing players
                for player_id in self.matches[match_id]["players"]:
                    if player_id != identifier:
                        player_info = self.matches[match_id]["players"][player_id]
                        try:
                            client.send(json.dumps({
                                "id": player_id,
                                "object": "player",
                                "username": player_info["username"],
                                "position": player_info["position"],
                                "health": player_info["health"],
                                "joined": True,
                                "left": False
                            }).encode("utf8"))
                            time.sleep(0.1)
                        except OSError:
                            pass

                # Add new player to players list, and letting it to receive messages from other players
                # self.players[new_id] = new_player_info
                self.matches[match_id]["players"][identifier] = new_player_info

                # Start thread to receive messages from client
                msg_thread = threading.Thread(target=self.handle_messages, args=(identifier, match_id), daemon=True)
                msg_thread.start()

                print(f"[+] New player connected (ID: {identifier}, MATCH: {match_id})")

    def handle_messages(self, identifier: str, match_identifier: str):
        """
        Receive and route player objects and maintain connection with client during the game
        :param identifier: The identifier of the user, -1 if it is a spectator
        :param match_identifier: The key that helps us understand how to route updates
        :return:
        """
        if identifier != "-1":
            client_info = self.matches[match_identifier]["players"][identifier]
            client: socket.socket = client_info["socket"]
            username = client_info["username"]
        else:
            # Spectator
            client: socket.socket = self.matches[match_identifier]["spectators"][-1]  # Last who joined

        while True:
            try:
                msg = client.recv(MSG_SIZE)
            except ConnectionResetError:
                break

            if not msg:
                break

            msg_decoded = msg.decode("utf8")

            try:
                left_bracket_index = msg_decoded.index("{")
                right_bracket_index = msg_decoded.index("}") + 1
                msg_decoded = msg_decoded[left_bracket_index:right_bracket_index]
            except ValueError:
                continue

            try:
                msg_json = json.loads(msg_decoded)
            except Exception as e:
                print(e)
                continue

            # print(f"[*] Received message from '{username}' with ID {identifier}")

            if msg_json["object"] == "player":
                # If the client moved, update it's information in the dict
                self.matches[match_identifier]["players"][identifier]["position"] = msg_json["position"]
                self.matches[match_identifier]["players"][identifier]["rotation"] = msg_json["rotation"]
                self.matches[match_identifier]["players"][identifier]["health"] = msg_json["health"]

            # Tell other players about an object moving
            for player_id in self.matches[match_identifier]["players"]:
                if player_id != identifier:
                    player_info = self.matches[match_identifier]["players"][player_id]
                    player_client: socket.socket = player_info["socket"]
                    try:
                        player_client.sendall(msg_decoded.encode("utf8"))
                    except OSError:
                        pass

            # Tell the same to the spectators because they are not in the player list
            for spectator_socket in self.matches[match_identifier]["spectators"]:
                try:
                    spectator_socket.sendall(msg_decoded.encode("utf8"))
                except OSError:
                    pass

        if identifier != "-1":
            # If a player leaves or an error occurred, tell other players about player leaving
            for player_id in self.matches[match_identifier]["players"]:
                if player_id != identifier:
                    player_info = self.matches[match_identifier]["players"][player_id]
                    player_client: socket.socket = player_info["socket"]
                    try:
                        player_client.send(
                            json.dumps({"id": identifier,
                                        "object": "player",
                                        "joined": False,
                                        "left": True}
                                       ).encode(
                                "utf8"))
                    except OSError:
                        pass
            for spectator_socket in self.matches[match_identifier]["spectators"]:
                try:
                    spectator_socket.send(
                        json.dumps({"id": identifier,
                                    "object": "player",
                                    "joined": False,
                                    "left": True}
                                   ).encode(
                            "utf8"))
                except OSError:
                    pass

            print(f"[-] Player '{username}' with ID {identifier} has left the match...")
            del self.matches[match_identifier]["players"][identifier]

        else:
            # if a spectator left
            print(f"[-] Spectator has left the match...")
            self.matches[match_identifier]["spectators"].remove(client)

        client.close()

    def spectator(self, match_id, client):
        """
        The idea of a spectator is receiving info about other objects but
        informing about yourself. So most actions are similar.
        :param client:
        :param match_id:
        :return:
        """
        if match_id in self.matches:
            for player_id in self.matches[match_id]["players"]:
                player_info = self.matches[match_id]["players"][player_id]
                try:
                    client.send(json.dumps({
                        "id": player_id,
                        "object": "player",
                        "username": player_info["username"],
                        "position": player_info["position"],
                        "health": player_info["health"],
                        "joined": True,
                        "left": False
                    }).encode("utf8"))
                    time.sleep(0.1)
                except OSError:
                    pass
        else:
            # Create new record for this match
            self.matches[match_id] = {"players": {}, "spectators": []}

        self.matches[match_id]["spectators"].append(client)
        print(f"[+] A spectator has joined to {match_id}")

        msg_thread = threading.Thread(target=self.handle_messages, args=("-1", match_id), daemon=True)
        msg_thread.start()


if __name__ == "__main__":
    try:
        g = GameServer()
        g.main()
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        print("Exiting")
