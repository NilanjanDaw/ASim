
import simpy
import numpy as np
from node import Node
from BroadcastMsg import BroadcastPipe
from random import shuffle

SIM_DURATION = 128000 #12800000
NODE_COUNT =  10

node_list = []

fail_stop = True
f = 0.05 # fraction of nodes controlled by adversary
f_adversary_list = []
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
        if fail_stop == False or (fail_stop == True and node.is_fail_stop_adversary == False) :
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

        else:
          if node.checkLeader():
            print("I'm byazntine Node {}, and I'm Leader".format(node.node_id))

        loop_counter += 1
        if len(node.blockchain) > 64:
            break

total_stake = 0

for node_id in range(NODE_COUNT):
    node = Node(node_id, env, statistical_delay, bc_pipe, bc_pipe_c, statistical_delay)
    node.populateNeighbourList(NODE_COUNT, 2, 4)
    total_stake += node.stake
    env.process(node.receiveBlock())
    env.process(node.message_consumer(bc_pipe.get_output_conn()))
    env.process(node.message_consumer_c(bc_pipe_c.get_output_conn()))
    node_list.append(node)

f_adversary_list = node_list
shuffle(f_adversary_list)
f_adversary_list = f_adversary_list[0:int(f*len(f_adversary_list))]
print("Number of nodes controlled by adversary:",len(f_adversary_list))

for node in node_list:
    node.total_stake = total_stake
    node.node_list = node_list
    if node in f_adversary_list:
      node.is_fail_stop_adversary = True


for node in node_list:
    env.process(start_simulation(env, node_list, node))

env.run(until=simpy.core.Infinity)

