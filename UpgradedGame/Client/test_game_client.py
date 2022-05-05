import socket
import json

from Client.Game.player import Player
from Client.Game.enemy import Enemy
from Client.Game.bullet import Bullet

info = json.load(open("servers_info.json"))["Game Server"]
ADDR = info["ip"]
PORT = info["port"]


class GameClient:
    def __init__(self, identifier: str, match_id: str):
        """
        A client class to abstract away socket functions and make communication with server easy

        server_addr (str): IPv4 address of the server
        server_port (int): Port at which server is running
        username (str): Username of this client's player
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = ADDR
        self.port = PORT
        self.match_id = match_id
        self.id = identifier
        self.recv_size = 2048


    def settimeout(self, value):
        self.client.settimeout(value)

    def connect(self):
        """
        Connect to the server and get a unique identifier
        """

        self.client.connect((self.addr, self.port))

        # Kind of 'login' into the lobby
        self.client.send(json.dumps({
            "match_id": self.match_id,
            "id": self.id,
        }).encode("utf8"))

    def receive_info(self):
        try:
            msg = self.client.recv(self.recv_size)
        except socket.error as e:
            print(e)

        if not msg:
            return None

        msg_decoded = msg.decode("utf8")

        left_bracket_index = msg_decoded.index("{")
        right_bracket_index = msg_decoded.index("}") + 1
        msg_decoded = msg_decoded[left_bracket_index:right_bracket_index]

        msg_json = json.loads(msg_decoded)

        return msg_json

    def send_player(self, player: Player):
        player_info = {
            "object": "player",
            "id": self.id,
            "position": (player.world_x, player.world_y, player.world_z),
            "rotation": player.rotation_y,
            "health": player.health,
            "joined": False,
            "left": False
        }
        player_info_encoded = json.dumps(player_info).encode("utf8")

        try:
            self.client.send(player_info_encoded)
        except socket.error as e:
            print(e)

    def send_bullet(self, bullet: Bullet):
        bullet_info = {
            "object": "bullet",
            "position": (bullet.world_x, bullet.world_y, bullet.world_z),
            "damage": bullet.damage,
            "direction": bullet.direction,
            "x_direction": bullet.x_direction
        }

        bullet_info_encoded = json.dumps(bullet_info).encode("utf8")

        try:
            self.client.send(bullet_info_encoded)
        except socket.error as e:
            print(e)

    def send_health(self, player: Enemy):
        health_info = {
            "object": "health_update",
            "id": player.id,
            "health": player.health
        }

        health_info_encoded = json.dumps(health_info).encode("utf8")

        try:
            self.client.send(health_info_encoded)
        except socket.error as e:
            print(e)
