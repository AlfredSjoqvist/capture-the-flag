#Alternative Game Boundary Solution:
if tank.body.position[0] > 8.9:
    tank.body.position = [8.9, tank.body.position[1]]
    
elif tank.body.position[0] < 0:
    tank.body.position = [0, tank.body.position[1]]

elif tank.body.position[1] > 8.9:
    tank.body.position = [tank.body.position[0], 8.9]
    
elif tank.body.position[1] < 0:
    tank.body.position = [tank.body.position[0], 0]