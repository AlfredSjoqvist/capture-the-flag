import pygame
from pygame.locals import *
from pygame.color import *
import pymunk
import math
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--singleplayer", action = "store_true", help = "Launch the game in singleplayer")
parser.add_argument("-m", "--multiplayer", action = "store_true", help = "Launch the game in multiplayer")

args = parser.parse_args()
#----- Initialisation -----#

#-- Initialise the display
pygame.init()
pygame.display.set_mode()

#-- Initialise the clock
clock = pygame.time.Clock()

#-- Initialise the physics engine
space = pymunk.Space()
space.gravity = (0.0,  0.0)
space.damping = 0.1 # Adds friction to the ground for all objects


#-- Import from the ctf framework
import ai
import images
import gameobjects
import maps
import menu_screen

#-- Constants
FRAMERATE = 50


#-- Music
# Backgroud music
pygame.mixer.music.load("Music/background.wav")
pygame.mixer.music.set_volume(0.8)      #lower volume for background music
pygame.mixer.music.play(-1)

# Bullet sound
    # Is in bullet class

# Win sound
    # is in tank class -> has_won()

# Explosion sound
explosion_sound = pygame.mixer.Sound("Music/explosion.wav")


#-- Variables
#   Define the current level
current_map         = maps.map0
#   List of all game objects
game_objects_list   = []
tanks_list          = []
ai_list             = []

#-- Resize the screen to the size of the current level
screen = pygame.display.set_mode(current_map.rect().size)

#-- Generate the background
background = pygame.Surface(screen.get_size())


#-- Copy the grass tile all over the level area
for x in range(0, current_map.width):
    for y in range(0,  current_map.height):
        # The call to the function "blit" will copy the image
        # contained in "images.grass" into the "background"
        # image at the coordinates given as the second argument
        background.blit(images.grass,  (x*images.TILE_SIZE, y*images.TILE_SIZE))

#-- Create the boxes
for x in range(0, current_map.width):
    for y in range(0,  current_map.height):
        # Get the type of boxes
        box_type  = current_map.boxAt(x, y)
        # If the box type is not 0 (aka grass tile), create a box
        if(box_type != 0):
            # Create a "Box" using the box_type, aswell as the x,y coordinates,
            # and the pymunk space
            box = gameobjects.get_box_with_type(x, y, box_type, space)
            game_objects_list.append(box)

#-- Create game boundaries
boundary_positions = [(x, y) 
                      for x in range(-2, current_map.width+2) 
                      for y in range(-2, current_map.width+2) 
                      if not (0 <= x < current_map.width 
                      and 0 <= y < current_map.height)]

# Loop through the game boundary positions and put stone boxes outside the map
for x, y in boundary_positions:
    boundary = gameobjects.get_box_with_type(x, y, 1, space)
    game_objects_list.append(boundary)


#-- Create the tanks
player_id = len(current_map.start_positions)-1
player_id_2 = len(current_map.start_positions)-2

# Loop over the starting poistion
for i in range(0, len(current_map.start_positions)):
    # Get the starting position of the tank "i"
    pos = current_map.start_positions[i]

    scoreboard = gameobjects.Scoreboard(pos[0] + 0.3, pos[1], images.new_scoreboard[0])
    # Create the tank, images.tanks contains the image representing the tank
    tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[i], space, scoreboard)



    if i == player_id:
        
        # Add the tank to the list of tanks
        player1 = tank
        tanks_list.append(tank)
        game_objects_list.append(tank)
    
    elif i == player_id_2 and args.multiplayer:

         # Add the tank to the list of tanks
        player2 = tank
        tanks_list.append(tank)
        game_objects_list.append(tank)

    else:
        
        # Add the AI tank to the AI list
        tank_ai = ai.Ai(tank, game_objects_list, ai_list, space, current_map)
        ai_list.append(tank_ai)
        game_objects_list.append(tank_ai.tank)
        tanks_list.append(tank_ai.tank)


#-- Create the flag
flag = gameobjects.Flag(current_map.flag_position[0], current_map.flag_position[1])
game_objects_list.append(flag)

#-- Display the bases
# Loop over the tank starting positions
for i in range(0, len(current_map.start_positions)):
    # Get the position of base "i"
    pos = current_map.start_positions[i]
    # Create the base
    base = gameobjects.GameVisibleObject(pos[0], pos[1], images.bases[i])
    # Add the base to the list of game objects
    game_objects_list.append(base)

#-- Display the menu

    screen_width, screen_height = pygame.display.get_surface().get_size()

    menu_objects_list = []
    button_x = screen_width//2

    button_y = screen_height//2
    play_button = menu_screen.MenuButton(button_x, button_y, "PLAY")

    menu_objects_list.append(play_button)


#-- Helper functions --#

def collide_bullet(arb, space, data):
    """Handle bullet collision"""
    collision_object = arb.shapes[1].parent

    # Remove the bullet from the screen display
    try:
        game_objects_list.remove(arb.shapes[0].parent)
    except ValueError:
        pass

    # Remove the bullet from the physics engine
    space.remove(arb.shapes[0], arb.shapes[0].body)

    # If it collides with a tank, respawn it
    if isinstance(collision_object, gameobjects.Tank):
        explosion_sound.play()
        collision_object.healthpoints -= 40
        collision_object.lasthit = 250
        if collision_object.healthpoints < 0:
            collision_object.healthpoints = 100
            explosion = gameobjects.Explosion(
                collision_object.body.position.x, 
                collision_object.body.position.y
                )
            game_objects_list.append(explosion)
            respawn_tank(collision_object)
    
    # If it collides with a wooden box, destroy it
    if isinstance(collision_object, gameobjects.Box):
        if collision_object.destructable:

            explosion = gameobjects.Explosion(
                collision_object.body.position.x,
                collision_object.body.position.y
                )
            game_objects_list.append(explosion)

            explosion_sound.play()
            destroy_box(arb, space)



    return True

def respawn_tank(tank, respawn_flag=False):
    """Reset tank position to the base"""
    # Respawn the tank

    death_positon = tank.body.position
    tank.respawn_shield_timer = 250

    # Set the flags new position depending on if the tank won or just got killed
    if respawn_flag:
        new_flag_pos = pymunk.Vec2d(current_map.flag_position[0], current_map.flag_position[1])
    else:
        new_flag_pos = pymunk.Vec2d(math.floor(death_positon.x)+0.5, math.floor(death_positon.y)+0.5)
    tank.body.position = tank.start_position
    tank.body.angle = tank.start_orientation
    tank.body.velocity = pymunk.Vec2d(0, 0)

    # If the tank carries the flag, reset the flag position
    if tank.flag:
        tank.flag.is_on_tank = False
        tank.flag.orientation = 0

        tank.flag.x, tank.flag.y = new_flag_pos.x, new_flag_pos.y
            
        tank.flag = None

def destroy_box(arb, space):
    """Destroy a box"""
    # Remove the box from the screen display
    game_objects_list.remove(arb.shapes[1].parent)

    pygame.mixer.Sound("Music/explosion.wav").play

    # Remove the box from the physics engine
    space.remove(arb.shapes[1], arb.shapes[1].body)

def tank_action(tank):
    """Handle all actions related to the player tank"""
    # Get all the currently held keys
    pressed = pygame.key.get_pressed()

    # Check if any arrow key is pressed
    if pressed[pygame.K_UP] or pressed[pygame.K_DOWN] or pressed[pygame.K_RIGHT] or pressed[pygame.K_LEFT]:
        
        # Check if up or down arrow key is pressed
        if pressed[pygame.K_UP] or pressed[pygame.K_DOWN]:

            # Move forward
            if pressed[pygame.K_UP]:
                tank.accelerate()
            
            # Move backward
            if pressed[pygame.K_DOWN]:
                tank.decelerate()
            
        # If up or down arrow keys are not pressed, stop velocity
        else:
            tank.stop_moving()
        
        # Check if left or right arrow key is pressed
        if pressed[pygame.K_RIGHT] or pressed[pygame.K_LEFT]:
        
            # Rotate clockwise
            if pressed[pygame.K_RIGHT]:
                tank.turn_right()
            
            # Rotate counter-clockwise
            if pressed[pygame.K_LEFT]:
                tank.turn_left()
        
        # If left or right arrow keys are not pressed, stop rotation
        else:
            tank.stop_turning()

    # If no arrow keys are pressed, stop all movement
    else:
        tank.stop_moving()
        tank.stop_turning()
    
    # If the A key is pressed and the shot isn't on cooldown, the player fires a bullet
    if pressed[pygame.K_l] and tank.shot_cooldown == 0:
        bullet = tank.shoot(space)
        game_objects_list.append(bullet)
        
        

    # If the tank has the flag, update the flag position
    tank.post_update()

def tank_action_2(tank):
    """Handle all actions related to the player tank"""
    # Get all the currently held keys
    pressed = pygame.key.get_pressed()

    # Check if any arrow key is pressed
    if pressed[pygame.K_w] or pressed[pygame.K_s] or pressed[pygame.K_d] or pressed[pygame.K_a]:
        
        # Check if up or down arrow key is pressed
        if pressed[pygame.K_w] or pressed[pygame.K_s]:

            # Move forward
            if pressed[pygame.K_w]:
                tank.accelerate()
            
            # Move backward
            if pressed[pygame.K_s]:
                tank.decelerate()
            
        # If up or down arrow keys are not pressed, stop velocity
        else:
            tank.stop_moving()
        
        # Check if left or right arrow key is pressed
        if pressed[pygame.K_d] or pressed[pygame.K_a]:
        
            # Rotate clockwise
            if pressed[pygame.K_d]:
                tank.turn_right()
            
            # Rotate counter-clockwise
            if pressed[pygame.K_a]:
                tank.turn_left()
        
        # If left or right arrow keys are not pressed, stop rotation
        else:
            tank.stop_turning()

    # If no arrow keys are pressed, stop all movement
    else:
        tank.stop_moving()
        tank.stop_turning()
    
    # If the A key is pressed and the shot isn't on cooldown, the player fires a bullet
    if pressed[pygame.K_v] and tank.shot_cooldown == 0:
        bullet = tank.shoot(space)
        game_objects_list.append(bullet)

    # If the tank has the flag, update the flag position
    tank.post_update()


def change_score(tank):    
    for tank in tanks_list:
        if tank.has_won():
            tank.scoreboard.add_score()
            tank.scoreboard.sprite = tank.scoreboard.show_score


# -- MAIN LOOP --

#-- Control whether the game run
running = True
menu_active = False
game_active = True
skip_update = 0

while running:
    


    if menu_active:
        for event in pygame.event.get():
            # Check if we receive a QUIT event (for instance, if the user press the
            # close button of the wiendow) or if the user press the escape key.
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False
        
            #-- Update Display
            screen.blit(background, (0,0))

            for obj in menu_objects_list:
                obj.update_screen(screen)


    if game_active:
        #-- Handle the events
        for event in pygame.event.get():
            # Check if we receive a QUIT event (for instance, if the user press the
            # close button of the wiendow) or if the user press the escape key.
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                running = False
            
            
            #++ Handle the tank movement
            tank_action(player1)

            if args.multiplayer:
                tank_action_2(player2)
                player2.try_grab_flag(flag)

            #++ See if the tank has grabbed the flag
            tank.try_grab_flag(flag)

            #++ See if the tank has won

            change_score(tank)

            for i in range(len(tanks_list)):
                victor = tanks_list[i]
                tank_number = i+1
                if victor.has_won():
                    pygame.mixer.Sound("Music/win_sound.wav").play()
                    print(f"Tank: {tank_number} has captured the flag!")
                    respawn_tank(victor, True)
                    print("New score:")
                    for a in range(len(tanks_list)):
                        current_tank = tanks_list[a]
                        tank_number = a+1
                        print(f"Tank {tank_number}: {current_tank.scoreboard.current_score}")
                    print("")


        #-- Collision Handler
        for n in range(1, 4):
            handler = space.add_collision_handler(1, n)
            handler.pre_solve = collide_bullet
        

        #-- Update physics
        if skip_update == 0:
            # Loop over all the game objects and update their speed in function of their
            # acceleration.
            for obj in game_objects_list:
                obj.update()

            skip_update = 2
        else:
            skip_update -= 1
        
        #-- Call decide function on AI every tick of the game
        for item in ai_list:
            item.decide()

        #   Check collisions and update the objects position
        space.step(1 / FRAMERATE)

    


        #   Update object that depends on an other object position (for instance a flag)
        for obj in game_objects_list:
            obj.post_update()
        
        #-- Update Display
        screen.blit(background, (0,0))

        # Update the display of the game objects on the screen
        for obj in game_objects_list:
            obj.update_screen(screen)

    

    #   Redisplay the entire screen (see double buffer technique)
    pygame.display.flip()

    #   Control the game framerate
    clock.tick(FRAMERATE)
