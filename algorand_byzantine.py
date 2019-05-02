
import simpy
import numpy as np
from node_byzantine import Node
from BroadcastMsg_byzantine import BroadcastPipe
from random import shuffle

SIM_DURATION = 128000 #12800000
NODE_COUNT =  10

node_list = []

a = 0.25 # fraction of nodes controlled by adversary
a_list = []
env = simpy.Environment()
mu = 200
signa = 400
statistical_delay = 200 #max(0, np.random.normal(mu, signa, 1)[0])
bc_pipe = BroadcastPipe(env)
bc_pipe_c = BroadcastPipe(env)

def printLog(node, loop_counter, env):
  

      print(env.now,
            ":",
            "blockchain:",
            node.node_id,
            ":",
            loop_counter,
            ":",
            len(node.blockchain),
            ":",
            node.blockchain)
        # print(env.now,
        #       ":",
        #       "blockcache:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockcache),
        #       ":",
        #       node.blockcache)
      print(env.now,
            ":",
            "blockcache_bc:",
            node.node_id,
            ":",
            loop_counter,
            ":",
            len(node.blockcache_bc),
            ":",
            node.blockcache_bc)
        # print(env.now,
        #       ":",
        #       "committeeBlockQueue_bc:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.committeeBlockQueue_bc),
        #       ":",
        #       node.committeeBlockQueue_bc)
        
        # print(env.now,
        #       ":",
        #       "highestpriority:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       node.get_hblock(clear=False))
      


def start_simulation(env, node_list, node):
    # TODO: Check this time out
    # This was a fix for improper starting of this function
    print("Node:", node.node_id, "started.......")
    yield env.timeout(0)
    loop_counter = 0
    # print(node.validatePayload(node.blockchain[0]))
    while True:
        block = node.priorityProposal(1) # 1 for vrf seed
        if block is not None:
            node.sendBlock(node_list, block)
        node.gossip_block = block

        # yield env.timeout(200)
        yield env.timeout(3000)

        # print("Node : {} , blockcache: {}".format(node.node_id,node.blockcache))
        if node.checkLeader():
            node.blockProposal()   

        yield env.timeout(3000)
        
        
        print(env.now,
              ":",
              "blockcache_bc:",
              node.node_id,
              ":",
              loop_counter,
              ":",
              len(node.blockcache_bc),
              ":",
              node.blockcache_bc)
        
        yield env.process(node.run_ba_star())

        print(env.now,
              ":",
              "blockchain:",
              node.node_id,
              ":",
              loop_counter,
              ":",
              len(node.blockchain),
              ":",
              node.blockchain)

        
        # node.round += 1
        # if node.checkLeader():
        #   print("I'm byazntine Node {}, and I'm Leader".format(node.node_id))

        loop_counter += 1
        if len(node.blockchain) > 64:
            break

total_stake = 0

for node_id in range(NODE_COUNT):
    node = Node(node_id, env, statistical_delay, bc_pipe, bc_pipe_c, statistical_delay)
    node.populateNeighbourList(NODE_COUNT, 2, 4)
    total_stake += node.stake
    env.process(node.receiveBlock())
    node_list.append(node)

l = list(range(NODE_COUNT))
shuffle(l)
l = l[0:int(a*len(l))]
print("Number of nodes controlled by adversary:",len(l))
for i in l:
  a_list.append(node_list[i])
print("Nodes controlled by A:",a_list)
for node in node_list:
    node.total_stake = total_stake
    node.node_list = node_list
    if node.node_id in l:
      node.a_list = a_list
      node.is_adversary = True
      env.process(node.message_consumer(bc_pipe.get_output_conn()))
      env.process(node.message_consumer_c(bc_pipe_c.get_output_conn()))


for node in node_list:
    env.process(start_simulation(env, node_list, node))

env.run(until=simpy.core.Infinity)

