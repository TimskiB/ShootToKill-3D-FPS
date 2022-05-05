from ursina import *
import os


class Map:
    def __init__(self):
        # 3 3D models that we give with textures
        floor = Entity(model="floor",
                       texture="floor.tif",
                       scale=20,
                       collider='mesh')
        external_walls = Entity(model="externals",
                                texture="external_wall.tif",
                                scale=20,
                                collider='mesh')
        internal_walls = Entity(model="walls",
                                texture="internal_wall.tif",
                                scale=20,
                                collider='mesh')
