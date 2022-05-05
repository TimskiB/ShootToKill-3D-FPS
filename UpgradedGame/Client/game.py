import socket
from threading import Thread

import ursina
from ursina import *
import sys
from Game.bullet import Bullet
from Game.map import Map
from Game.player import Player
from Game.sky import Sky
from game_client import GameClient
from Game.enemy import Enemy

if len(sys.argv) > 1:
    # If received match id, we want to create for it a client
    match_id = sys.argv[1]
    user_id = sys.argv[2]
    print(f"[+] Initializing match {match_id} (For user {user_id})")
    client = GameClient(user_id, match_id)
    client.connect()

app = Ursina()

window.borderless = False  # Can be fullscreened, turned off for debugging
window.title = "Shoot To Kill"
window.exit_button.visible = True
game_map = Map()  # Create all map object
game_sky = Sky()  # Create sky object
if user_id != "-1":
    # If we are not a spectator
    player = Player(Vec3(0, 10, 0))
    player.world_rotation_y = 0
    prev_pos = player.world_position
    prev_dir = player.world_rotation_y

else:
    # Spectator shall be a normal player but with disabled options
    player = Player(Vec3(0, 50, 0), True)
    player.world_rotation_x = 90
    player.world_rotation_y = 0
    prev_pos = player.world_position
    prev_dir = player.world_rotation_y
    EditorCamera()  # Give the player the option to fly around with the right key
enemies = []  # For further updates it is a list


def update():
    """
    Each and every moment this function is called and runs its body code, that let's us sending our new location
    (if we are alive)
    :return:
    """
    if user_id != "-1":
        if player.health > 0:
            global prev_pos, prev_dir

            if prev_pos != player.world_position or prev_dir != player.world_rotation_y:
                client.send_player(player)

            prev_pos = player.world_position
            prev_dir = player.world_rotation_y


def input(key):
    """
    This function gets automatically called when a key is pressed
    :param key: The name of the key that was pressed
    :return:
    """
    if user_id != "-1":
        # If we are not a spectator
        if key == "left mouse down" and player.health > 0 and user_id != "-1":
            # If a player wants to shoot and he is not dead
            start_position = player.position + ursina.Vec3(0, 2, 0)  # Define the start location of the bullet
            new_bullet = Bullet(start_position, player.world_rotation_y,
                                -player.camera_pivot.world_rotation_x, client)  # Add parameter client (for network)
            client.send_bullet(new_bullet)

            # Bullet will be destroyed after 3 second because it already flew out of the map
            ursina.destroy(new_bullet, delay=2)


def receive():
    """
    This function connects between backend and frontend by receiving messages and translating them to game graphics
    :return:
    """
    while True:
        try:
            info = client.receive_info()
        except Exception as e:
            print(e)
            continue

        if not info:
            print("[-] Game Server has stopped responding, Exiting game...")
            sys.exit()

        if info["object"] == "player":
            # If there is an update about a player
            enemy_id = info["id"]

            if info["joined"]:
                # If a player just joined and we need to create it's object
                new_enemy = Enemy(ursina.Vec3(*info["position"]), enemy_id, info["username"])
                new_enemy.health = info["health"]
                enemies.append(new_enemy)
                continue

            enemy = None

            for e in enemies:
                if e.id == enemy_id:
                    enemy = e
                    break

            if not enemy:
                continue

            if info["left"]:
                # Destroy their object if they left the game
                enemies.remove(enemy)
                ursina.destroy(enemy)
                continue

            # Update position and rotation
            enemy.world_position = ursina.Vec3(*info["position"])
            enemy.rotation_y = info["rotation"]

        elif info["object"] == "bullet":
            # IF the information is about a bullet, create it's object
            b_pos = ursina.Vec3(*info["position"])
            b_dir = info["direction"]
            b_x_dir = info["x_direction"]
            b_damage = info["damage"]
            new_bullet = Bullet(b_pos, b_dir, b_x_dir, client, b_damage, slave=True)
            ursina.destroy(new_bullet, delay=2)

        elif info["object"] == "health_update":
            # Change the health of an enemy
            enemy_id = info["id"]

            enemy = None

            if enemy_id == client.id:
                enemy = player
            else:
                for e in enemies:
                    if e.id == enemy_id:
                        enemy = e
                        break

            if not enemy:
                continue

            enemy.health = info["health"]


def Main():
    # Start receiving
    msg_thread = Thread(target=receive, daemon=True)
    msg_thread.start()
    app.run()


if __name__ == "__main__":
    Main()
