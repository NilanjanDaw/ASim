
import simpy
import numpy as np
from node import Node, start_simulation
SIM_DURATION = 25000
NODE_COUNT = 10
node_list = []


env = simpy.Environment()
mu = 200
signa = 400
statistical_delay = max(0, np.random.normal(mu, signa, 1)[0])
for node_id in range(NODE_COUNT):
    node = Node(node_id, env, statistical_delay)
    node.populateNeighbourList(NODE_COUNT, 4, 8)
    env.process(node.receiveBlock())
    node_list.append(node)
for node in node_list:
    env.process(start_simulation(env, node_list, node))

env.run(until=SIM_DURATION)