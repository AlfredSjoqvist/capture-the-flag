import pygame
import math
import images
import pymunk
from gameobjects import *
from images import menu_button as menu_button_sprite







class MenuButton(GameObject):
    
    def __init__(self, x, y, text):



        self.width = 100
        self.height = 20

        button_sprite = pygame.transform.scale(menu_button_sprite, (self.width, self.height))


        super().__init__(button_sprite)

        self.position = x, y
        self.angle = math.radians(0)
        self.text = text

    def screen_position(self):
        """ Converts the body's position in the physics engine to screen coordinates. """
        return physics_to_display(self.position)
    
    def screen_orientation(self):
        """ Angles are reversed from the engine to the display. """
        return -math.degrees(self.angle)
    








