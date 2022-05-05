from random import randint
from ursina import *

from Game.enemy import Enemy


class Bullet(Entity):

    def __init__(self, position: Vec3, direction: float, x_direction: float, client,
                 damage: int = randint(5, 20), slave=False):
        """
        This class defines the each bullet object, manages it's movement and collisions
        :param position: The x,y,z that the bullet starts from
        :param direction: The direction the player looks at and the direction the bullet is flying to
        :param x_direction:
        :param network: The socket is here in order to update the health of the enemy if they are hit
        :param damage: The damage the bullet will give when hit
        :param slave:
        """
        speed = 50  # Bullet speed can be changed

        """Calculations section"""
        dir_rad = math.radians(direction)
        x_dir_rad = math.radians(x_direction)

        self.velocity = Vec3(
            math.sin(dir_rad) * math.cos(x_dir_rad),
            math.sin(x_dir_rad),
            math.cos(dir_rad) * math.cos(x_dir_rad)
        ) * speed

        """"""

        super().__init__(
            position=position + self.velocity / speed,
            model="sphere",
            collider="box",
            scale=0.2
        )  # The spawn of the object in the map

        # Save properties
        self.damage = damage
        self.direction = direction
        self.x_direction = x_direction
        self.slave = slave
        self.client = client

    def update(self):
        """
        This function always runs itself and it checks if the bullet has hit the enemy
        :return:
        """

        self.position += self.velocity * time.dt
        hit_info = self.intersects()

        if hit_info.hit:  # True if bullet is touching something
            if not self.slave:
                for entity in hit_info.entities:  # Check for object in the map if it is an enemy object
                    if isinstance(entity, Enemy):
                        entity.health -= self.damage
                        self.client.send_health(entity)  # Inform enemy that he was hit

            destroy(self)  # If bullet touches anything, even a wall, it shall be destroyed
