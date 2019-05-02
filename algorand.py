
import simpy
import numpy as np
from node import Node
from BroadcastMsg import BroadcastPipe
SIM_DURATION = 1200000
NODE_COUNT = 10
node_list = []


env = simpy.Environment()
mu = 200
signa = 400
statistical_delay = max(0, np.random.normal(mu, signa, 1)[0])
bc_pipe = BroadcastPipe(env)
bc_pipe_c = BroadcastPipe(env)


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
        yield env.timeout(2000)
        # print("Node : {} , blockcache: {}".format(node.node_id,node.blockcache))
        if node.checkLeader():
            node.blockProposal()
        
        if node.committeeSelection():
            print("Node : {} , in Committee".format(node.node_id))
            yield env.timeout(33) # should be 33 seconds
            # cast vote
            # node.castVote()

        break
        
        # yield env.timeout(1000)

        # Logging states of nodes

        # print("blockchain:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockchain),
        #       ":",
        #       node.blockchain)
        # print("blockcache:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockcache),
        #       ":",
        #       node.blockcache)
        # print("blockcache_bc:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockcache_bc),
        #       ":",
        #       node.blockcache_bc)
        # print("committeeBlockQueue_bc:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.committeeBlockQueue_bc),
        #       ":",
        #       node.committeeBlockQueue_bc)
        
        # print("highestpriority:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       node.get_hblock(clear=False))

        # print(env.now,
        #       ":",
        #       "blockchain:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockchain),
        #       ":",
        #       node.blockchain)
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
        # print(env.now,
        #       ":",
        #       "blockcache_bc:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       len(node.blockcache_bc),
        #       ":",
        #       node.blockcache_bc)
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
        

        yield env.process(node.run_ba_star())

        # print(env.now,
        #       ":",
        #       "highestpriority:",
        #       node.node_id,
        #       ":",
        #       loop_counter,
        #       ":",
        #       node.get_hblock(clear=False))
        
        # node.run_ba_star()
        # self.blockchain = []
        # self.blockcache = []
        # self.blockcache_bc = []
        # self.committeeBlockQueue_bc = []

        # if node.committeeSelection():
        #     yield env.timeout(33) # should be 33 seconds
        #     # cast vote
        #     node.castVote()
        loop_counter += 1

total_stake = 0

for node_id in range(NODE_COUNT):
    node = Node(node_id, env, statistical_delay, bc_pipe, bc_pipe_c)
    node.populateNeighbourList(NODE_COUNT, 4, 8)
    total_stake += node.stake
    env.process(node.receiveBlock())
    env.process(node.message_consumer(bc_pipe.get_output_conn()))
    env.process(node.message_consumer_c(bc_pipe_c.get_output_conn()))
    node_list.append(node)

for node in node_list:
    node.total_stake = total_stake
    node.node_list = node_list

for node in node_list:
    env.process(start_simulation(env, node_list, node))

env.run(until=SIM_DURATION)