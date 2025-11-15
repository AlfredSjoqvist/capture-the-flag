import math
import pymunk
from pymunk import Vec2d
import gameobjects
from collections import defaultdict, deque

# NOTE: use only 'map0' during development!

MIN_ANGLE_DIF = math.radians(3) # 3 degrees, a bit more than we can turn each tick



def angle_between_vectors(vec1, vec2):
    """ Since Vec2d operates in a cartesian coordinate space we have to
        convert the resulting vector to get the correct angle for our space.
    """
    vec = vec1 - vec2 
    vec = vec.perpendicular()
    return vec.angle

def periodic_difference_of_angles(angle1, angle2): 
    return  (angle1% (2*math.pi)) - (angle2% (2*math.pi))


class Ai:
    """ A simple ai that finds the shortest path to the target using 
    a breadth first search. Also capable of shooting other tanks and or wooden
    boxes. """

    def __init__(self, tank,  game_objects_list, tanks_list, space, currentmap):
        self.tank               = tank
        self.game_objects_list  = game_objects_list
        self.tanks_list         = tanks_list
        self.space              = space
        self.currentmap         = currentmap
        self.flag = None
        self.MAX_X = currentmap.width - 1 
        self.MAX_Y = currentmap.height - 1

        self.path = deque()
        self.move_cycle = self.move_cycle_gen()
        self.update_grid_pos()

    def update_grid_pos(self):
        """ This should only be called in the beginning, or at the end of a move_cycle. """
        self.grid_pos = self.get_tile_of_position(self.tank.body.position)

    def decide(self):
        """ Main decision function that gets called on every tick of the game. """

        self.maybe_shoot()
        next(self.move_cycle)
        
        


    def maybe_shoot(self):
        """ Makes a raycast query in front of the tank. If another tank
            or a wooden box is found, then we shoot. 
        """
        x, y = self.tank.body.position

        angle = self.tank.body.angle
    
        self.orientation = self.tank.body.angle + math.radians(45)

        #Use same calculation as bullet spawn for finding front of tank
        start_x = x - math.cos((angle - (math.pi)/2)) * 0.3

        start_y = y - math.sin((angle - (math.pi)/2)) * 0.3

        start = start_x, start_y

        #Find end of ray casting using map.size
        end_x = x - math.cos((angle - (math.pi)/2)) * (self.currentmap.width**2 * self.currentmap.height**2)**0.5

        end_y = y - math.sin((angle - (math.pi)/2)) * (self.currentmap.width**2 * self.currentmap.height**2)**0.5

        end = end_x, end_y
        
        ray = self.space.segment_query_first(start, end, 0, pymunk.ShapeFilter())

        #Check if ray has .shape and if ray is movable box or tank. shoot if no cooldown
        if hasattr(ray, "shape"):
            if isinstance(ray.shape.parent, gameobjects.Box):
                if ray.shape.parent.movable:
                    if self.tank.shot_cooldown == 0:
                        bullet = self.tank.shoot(self.space)
                        self.game_objects_list.append(bullet)
            
            elif isinstance(ray.shape.parent, gameobjects.Tank):
                if self.tank.shot_cooldown == 0:
                    bullet = self.tank.shoot(self.space)
                    self.game_objects_list.append(bullet)
            

    def move_cycle_gen (self):
        """ A generator that iteratively goes through all the required steps
            to move to our goal.
        """      
        while True:
            
            last_position = (-1, -1)
            self.grid_pos = self.get_tile_of_position(Vec2d(self.tank.body.position))
            self.target = self.get_target_tile()
            self.path = self.find_shortest_path(self.target)

            #Set tank path to flag or base depending on flag status
            if not self.has_shortest_path():
                flag = self.get_flag()
                self.tank.try_grab_flag(flag)
                yield
                continue

            next_coord = self.path.popleft()

            #Turn until correct angle
            correct_angle = self.get_angle(next_coord)
            while not self.check_angle(correct_angle):
                
                self.cease_accelerate()
                self.turn(correct_angle)
                yield

            #Move until correct position
            while not self.correct_pos(next_coord, last_position):
                self.cease_turn()
                last_position = self.tank.body.position
                self.accelerate()
                yield


    def has_shortest_path(self):
        '''Return true or false if tank has shortest_path'''
        if len(self.find_shortest_path(self.get_target_tile())) != 0:
            return True
        else:
            return False


    def correct_pos(self, next_coord, last_position):
        '''Return true or false if tank has driven past the next position'''
        #Convert all values to Vec2d
        center = next_coord + Vec2d(0.5, 0.5)
        current_tank_vector = Vec2d(self.tank.body.position[0], self.tank.body.position[1])
        last_tank_vector = Vec2d(last_position[0], last_position[1])

        #Get distance to the next coordinate and the previous coordinate
        current_distance = center.get_distance(current_tank_vector)
        last_distance = center.get_distance(last_tank_vector)

        #If tank has driven past the correct position, return True
        if current_distance > last_distance:
            return True
        else:
            return False


    def check_angle(self, correct_angle):
        '''Check difference between target tile and current angle'''
        angle_offset = abs(periodic_difference_of_angles(self.tank.body.angle, correct_angle))

        return 0.05 > angle_offset

    def get_angle(self, next_coord):
        '''Return angle for next coord'''
        if next_coord.x > self.grid_pos.x:
            correct_angle = math.radians(270)
        elif next_coord.x < self.grid_pos.x:
            correct_angle = math.radians(90)
        elif next_coord.y > self.grid_pos.y:
            correct_angle = math.radians(0)
        elif next_coord.y < self.grid_pos.y:
            correct_angle = math.radians(180)
        else:
            correct_angle = math.radians(0)

        return correct_angle


    def turn(self, correct_angle):
        '''Check what direction tank has to turn and turn'''
        angle_dif = periodic_difference_of_angles(self.tank.body.angle, correct_angle) % (2 * math.pi)

        if math.radians(180) < angle_dif < math.radians(360):
            self.tank.turn_right()

        elif math.radians(0) < angle_dif < math.radians(180):
            self.tank.turn_left()

    
    def cease_turn(self):
        '''Make tank stop turning'''
        self.tank.stop_turning()


    def accelerate(self):
        '''Make tank accelerate'''
        self.tank.accelerate()

    def cease_accelerate(self):
        '''Make tank stop accelerating'''
        self.tank.stop_moving()

    def find_shortest_path(self, target):
        """ A simple Breadth First Search using integer coordinates as our nodes.
            Edges are calculated as we go, using an external function.
        """
        # Get the tank position
        start = self.grid_pos

        # Convert the start position from a vector to a typle so it is hashable
        start_tuple = start.x, start.y

        # Create the queue for the tiles that are about to be searched
        queue = deque([(start, [start])])

        # Create a set for the nodes that have already been visited
        already_visited = set(start_tuple)

        self.metalboxes_passable = False

        shortest_path = None

        # Loop through the queue
        while queue:

            # Save the node and the path to the tile and pop the element
            node, node_path = queue.popleft()

            # Break the loop if the current tile matches with the target
            if node == target:
                shortest_path = node_path[1:]
                break
                
            # Check the neighbors of the current tile
            for neighbor in self.get_tile_neighbors(Vec2d(node[0], node[1])):
                
                # Convert the neighbor to a tuple so it's hashable
                neighbor_tuple = neighbor.x, neighbor.y
                
                # Check if the neighbor has already been visited
                if not neighbor_tuple in already_visited:
                    
                    # Add the next tiles, and their corresponding path, to the queue
                    neighbor_path = node_path + [neighbor]
                    queue.append((neighbor, neighbor_path))
                    already_visited.add((neighbor_tuple))
            
            # If the pathfinder goes through all possible paths and can't find anything, try to pathfind through metal boxes as well
            if not queue and not self.metalboxes_passable:
                self.metalboxes_passable = True
                queue = deque([(self.grid_pos, [self.grid_pos])])
                already_visited = set(start_tuple)
            
            # If the queue is empty and no path has been found, start over the pathfindes
            if not queue and self.metalboxes_passable:
                queue = deque([(self.grid_pos, [self.grid_pos])])
                already_visited = set(start_tuple)
            

        return deque(shortest_path)
            

    def get_target_tile(self):
        """ Returns position of the flag if we don't have it. If we do have the flag,
            return the position of our home base.
        """
        if self.tank.flag != None:
            x, y = self.tank.start_position
        else:
            self.get_flag() # Ensure that we have initialized it.
            x, y = self.flag.x, self.flag.y
        return Vec2d(int(x), int(y))


    def get_flag(self):
        """ This has to be called to get the flag, since we don't know
            where it is when the Ai object is initialized.
        """
        if self.flag == None:
        # Find the flag in the game objects list
            for obj in self.game_objects_list:
                if isinstance(obj, gameobjects.Flag):
                    self.flag = obj
                    break
        return self.flag


    def get_tile_of_position(self, position_vector):
        """ Convert and return the float position of our tank to an integer position. """
        x, y = position_vector
        return Vec2d(int(x), int(y))


    def get_tile_neighbors(self, coord_vec):
        """ Returns all bordering grid squares of the input coordinate.
            A bordering square is only considered accessible if it is grass
            or a wooden box.
        """
        x = coord_vec.x
        y = coord_vec.y

        # Find the coordinates of the tiles' four neighbors
        # Start with the tile above the tank and goes clockwise from there
        north_tile = Vec2d(x, y - 1)
        east_tile = Vec2d(x + 1, y)
        south_tile = Vec2d(x, y + 1)
        west_tile = Vec2d(x - 1, y)

        neighbors = [north_tile, east_tile, south_tile, west_tile] 

        return list(filter(self.filter_tile_neighbors, neighbors))


    def filter_tile_neighbors(self, coord):
        '''Check if neighbor tiles are box or grass'''
        x = coord.x
        y = coord.y

        # If a tile can't be found at the coordinate, set the box type to a rockbox
        try:
            box_type = self.currentmap.boxAt(x, y)
        except IndexError:
            box_type = 1
        
        # If the map contains a lot of metal boxes, count them as passable
        if self.metalboxes_passable:
            barrier_types = [1]
        else:
            barrier_types = [1, 3]

        # If the tile contains a passable neighbour return True
        if (box_type in barrier_types or 
            x > self.MAX_X or 
            y > self.MAX_Y or 
            x < 0 or 
            y < 0):
            
            return False
        else:
            return True


SimpleAi = Ai # Legacy