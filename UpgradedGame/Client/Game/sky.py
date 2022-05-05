from ursina import *


class Sky:
    def __init__(self):
        # Create sky object
        sky = Entity(
            model="sphere",
            texture="sky.png",
            scale=9999,
            double_sided=True
        )
