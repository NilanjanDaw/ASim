
import simpy
import numpy as np
from node import Node
from BroadcastMsg import BroadcastPipe
SIM_DURATION = 2500
NODE_COUNT = 10
node_list = []


env = simpy.Environment()
mu = 200
signa = 400
statistical_delay = max(0, np.random.normal(mu, signa, 1)[0])
bc_pipe = BroadcastPipe(env)
def start_simulation(env, node_list, node):
    print(node.validatePayload(node.blockchain[0]))
    while True:
        block = node.priorityProposal(1)
        if block is not None:
            node.sendBlock(node_list, block)
        node.gossip_block = block
        yield env.timeout(200)
        if node.checkLeader():
            node.blockProposal()

for node_id in range(NODE_COUNT):
    node = Node(node_id, env, statistical_delay, bc_pipe)
    node.populateNeighbourList(NODE_COUNT, 4, 8)
    env.process(node.receiveBlock())
    env.process(node.message_consumer(bc_pipe.get_output_conn()))
    node_list.append(node)
for node in node_list:
    env.process(start_simulation(env, node_list, node))

env.run(until=SIM_DURATION)