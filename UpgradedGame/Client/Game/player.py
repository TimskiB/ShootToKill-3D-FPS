import ursina
from ursina.prefabs.first_person_controller import FirstPersonController


class Player(FirstPersonController):
    def __init__(self, position: ursina.Vec3, spectator=False):
        super().__init__(
            position=position,
            model="cube",
            jump_height=2.5,
            jump_duration=0.4,
            origin_y=-2,
            collider="box",
            speed=7,
        )
        self.spectator = spectator
        if not spectator:
            self.cursor.color = ursina.color.rgb(255, 0, 0, 122)

            self.gun = ursina.Entity(
                parent=ursina.camera.ui,
                position=ursina.Vec2(0.65, -0.4),
                scale=ursina.Vec3(0.1, 0.2, 0.65),
                rotation=ursina.Vec3(0, -2, 0),
                model="Colt1911final",
                texture="gun.png",
                color=ursina.color.color(0, 0, 0.4)
            )

            self.healthbar_pos = ursina.Vec2(0, 0.45)
            self.healthbar_size = ursina.Vec2(0.8, 0.04)
            self.healthbar_bg = ursina.Entity(
                parent=ursina.camera.ui,
                model="quad",
                color=ursina.color.rgb(255, 0, 0),
                position=self.healthbar_pos,
                scale=self.healthbar_size
            )
            self.healthbar = ursina.Entity(
                parent=ursina.camera.ui,
                model="quad",
                color=ursina.color.rgb(0, 255, 0),
                position=self.healthbar_pos,
                scale=self.healthbar_size
            )

            self.health = 100
        self.death_message_shown = False

    def death(self):
        if not self.spectator:
            self.death_message_shown = True

            ursina.destroy(self.gun)
            self.rotation = 0
            self.camera_pivot.world_rotation_x = -45
            self.world_position = ursina.Vec3(0, 7, -35)
            self.cursor.color = ursina.color.rgb(0, 0, 0, a=0)

            ursina.Text(
                text="You are dead!",
                origin=ursina.Vec2(0, 0),
                scale=3
            )

    def update(self):
        if not self.spectator:
            self.healthbar.scale_x = self.health / 100 * self.healthbar_size.x

            if self.health <= 0:
                if not self.death_message_shown:
                    self.death()
            else:
                super().update()
