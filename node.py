import ecdsa
import network
from random import randint, shuffle
from helper import *
import hashlib
import math




# Constants
# Expected committee size
TAU_PROPOSER = 5
TAU_STEP = 32


# Majority fraction of votes for BA*, T_FRACTION > 2/3(0.666....)
T_FRACTION = 20/100

# (milliseconds), Wait for this time to listen to priorities broadcast
LAMBDA_PROPOSER = 3000

# (milliseconds), Wait for LAMBDA_PROPOSER + LAMBDA_BLOCK = 33seconds to get a
# block proposal from highest priority node else commit for empty block
LAMBDA_BLOCK = 30000

# Maximum number of steps for BinaryBA*
MAX_STEPS = 10

# Genesis String
genesis_string = "We are building the best Algorand Discrete Event Simulator"

class Node:
    def __init__(self, node_id, env, network_delay, bc_pipe, bc_pipe_c, statistical_delay):
        self.node_id = node_id
        self.private_key = None
        self.public_key = None
        self.round = 0
        self.stake = randint(1, 50)
        self.total_stake = 0
        self.cable = network.Network(env, network_delay)
        self.gossip_block = None
        self.neighbourList = []
        self.blockchain = []
        self.blockcache = []
        self.blockcache_bc = []
        self.committeeBlockQueue_bc = []
        self.broadcastpipe = bc_pipe #same pipe for all senders
        self.broadcastpipe_committee = bc_pipe_c
        self.env = env
        self.node_list = []
        self.delay = statistical_delay
        self.is_fail_stop_adversary = False
        self.generateCryptoKeys()
        genesis_block = {"prev_hash": 0, "payload": genesis_string}
        self.blockchain.append(genesis_block)
        print("Node {} has {} stake".format(self.node_id, self.stake))

    def generateCryptoKeys(self):
        self.private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        self.public_key = self.public_key.to_pem()
        self.private_key = self.private_key.to_pem()
        # print(self.public_key, self.private_key)
    
    def populateNeighbourList(self, node_count, neighbour_min, neighbour_max):

        neighbour_count = randint(neighbour_min, neighbour_max)
        x = [i for i in range(node_count)]
        x.remove(self.node_id)
        shuffle(x)
        self.neighbourList = x[:neighbour_count]
        print("Node {} neighbour list".format(self.node_id),
              self.neighbourList)


    def signPayload(self, payload):
        sk = ecdsa.SigningKey.from_pem(self.private_key) 
        signature = sk.sign(str.encode(payload))
        return signature
    
    # def formMessage(self, payload):
    #     msg = {
    #         "payload": payload,
    #         "public_key": self.public_key,
    #         "signature": self.signPayload(payload).hex()
    #     }
    #     return msg
    
    def validatePayload(self, payload):
        verifying_key = ecdsa.VerifyingKey.from_pem(payload['public_key'])
        return verifying_key.verify(bytes.fromhex(payload["signature"]), payload["payload"].encode())
    

    
    def priorityProposal(self, step):
        seed = vrf_seed(self.last_block_hash, self.round, step)
        j, vrf_hash = sortition(self.private_key, seed, TAU_PROPOSER,
                                self.stake, self.total_stake)
        print(self.stake)
        stake_subuser[self.stake] += j
        print("Priority Proposal Node {}, Round {}, Step {}, subusers {}".format(self.node_id, self.round, step, j))
        if j > 0:
            max_priority, subuser_index = self.getPriority(vrf_hash, j)
            gossip_message = self.generateGossipMessage(vrf_hash, subuser_index, max_priority)
            # print("Node id : {} Block ready to be gossiped:".format(self.node_id))
            return gossip_message
        else:
            # print("Node {} not selected for this round".format(self.node_id))
            return None

    def blockProposal(self):
        # print("block proposal started")
        # "<SHA256(Previous block)||256 bit long random string || Node’s Priority payload>"
        priority = self.gossip_block["priority"]
        message = {
            "hash_prev_block": hashlib.sha256(str(self.blockchain[-1]).encode()).hexdigest(), 
            "payload": prg(13),
            "round": self.round,
            "priority": priority,

        }
        self.message_generator(self.broadcastpipe, message)
        # print("block proposal done")
    
    def message_generator(self, out_pipe, message):
        # This is the transmission delay but set it according to message length
        # yield env.timeout(random.randint(6, 10))
        # time = int(len(str(message))/32) # 16 char per sec transmission speed
        # print("time calculated using bandwidth:",time,message,len(str(message)))
        # yield env.timeout(time)
        self.env.timeout(self.delay)
        out_pipe.put(message)


    def message_consumer(self, in_pipe):
        while True:
            msg = yield in_pipe.get()
            # print("msg receive--------------------------------")
            self.blockcache_bc.append(msg)
            # print('received message: %s.' %(msg))

    def message_generator_c(self, out_pipe, message):
        yield self.env.timeout(self.delay)
        out_pipe.put(message)


    def message_consumer_c(self, in_pipe):
        while True:
            msg = yield in_pipe.get()
            # print("msg receive----committee----------------")
            self.committeeBlockQueue_bc.append(msg)
            # print('received message: %s.' %(msg))


    def getPriority(self, vrf_hash, subuser_count):
        priority = -1
        subuser_index = -1
        for i in range(0, subuser_count + 1):
            sub_priority = hashlib.sha256((vrf_hash + str(i)).encode()).hexdigest()
            if priority == -1 or int(sub_priority, 16) < int(priority, 16):
                priority = sub_priority
                subuser_index = i
                # print("subpriority:", sub_priority)
        # print("max_priority:", priority)
        return priority, subuser_index

    def sendBlock(self, node_list, block):
        for id in self.neighbourList:
            node_list[id].cable.put(block)
        return 0
    
    def receiveBlock(self):
        while True:
            block = yield self.cable.get()
            if block is not None:
                # print("{} received block {}".format(self.node_id, block))
                # 1. validate
                if block not in self.blockcache:
                    self.blockcache.append(block)
                    # print("Node id: {} , I will gossip block to my nbs {}".format(self.node_id, self.neighbourList))
                    self.sendBlock(self.node_list, block)

    def generateGossipMessage(self, vrf_hash, subuser_index, priority):
        message = {
            "round_number": self.round,
            "vrf_hash": vrf_hash,
            "subuser_index": subuser_index,
            "priority": priority
        }
        return message

    # BUG: Why empty block require step & vrf_hash?? This will create a
    #        different empty block for each user and no one will ever reach
    #        consensus.
    def generateEmptyBlock(self, hash_prev_block, round, step, vrf_hash):
        seed = vrf_seed(hash_prev_block, self.round, step)
        j, vrf_hash = sortition(self.private_key, seed, TAU_PROPOSER,
                                self.stake, self.total_stake)
        stake_subuser[self.stake] += j
        print("Node {}, Round {}, Step {}, subusers {}", self.node_id, self.round, step, j)
        # change it to json format
        message = {
            "hash_prev_block": hashlib.sha256(self.blockchain[-1]),
            "round" : self.round,
            "step" : self.step,
            "msg" : "Empty", 
            "vrf_hash" : vrf_hash,
        }
        return message

    def sortGetElement(self, element):
        return element["priority"]

    def checkLeader(self):
        self.blockcache.sort(key=self.sortGetElement, reverse=True)
        print("Received Proposals", self.blockcache)
        if self.gossip_block is not None:
            if len(self.blockcache) > 0:
                priority = min (block["priority"] for block in self.blockcache)
                if self.gossip_block["priority"] <= priority:
                    print("Round {} Node {} selected as leader".format(self.round, self.node_id))
                    self.blockcache = []
                    return True
            else:
                print("blockcache empty")
        # else:
            # print("Node {} is not a proposer for round: {}".format(self.node_id, self.round))
        
        self.blockcache = []
        return False

    def committeeSelection(self):
        seed = hashlib.sha256(str(self.blockchain[-1]).encode()).hexdigest() + str(self.round) + "1"
        value = prg(seed)
        # seed = vrf_seed(self.last_block_hash, self.round, step)
        j, vrf_hash = sortition(self.private_key, value, TAU_PROPOSER,
                                self.stake, self.total_stake)
        stake_subuser[self.stake] += j
        print("Committee Selection Node {}, Round {}, subusers {}".format(self.node_id, self.round, j))
        # do cryptographic sortition , use tau_step
        # return True/False based on selection
        if j > 0:
            return True
        return False 

    def reduction(self, hblock):
        """
        Performs Reduction.

        Arguments:
        hblock -- hash of Highest priority block

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """

        # TODO: Get highest priority block

        self.committee_vote("reduction_1", TAU_STEP, hblock)

        # TODO: Search tag "where_timeout".
        #       Possible timeout needed, my doubt is where is it needed. This
        #       node waits for lamda_block + lamda_step seconds before
        #       counting for votes. Should timeout here or inside count_vote
        #       function. Add timeout of lamda_block + lamda_step
        
        hblock_1 = yield self.env.process(self.count_votes("reduction_1", T_FRACTION, TAU_STEP,
                                 LAMBDA_BLOCK + LAMBDA_PROPOSER))

        # FIXME: Why empty block require step & vrf_hash??
        empty_block  = self.empty_block
        if not hblock_1:
            self.committee_vote("reduction_2", TAU_STEP, empty_block )
        else:
            self.committee_vote("reduction_2", TAU_STEP, hblock_1)

        # TODO: Same issue as search tag "where_timeout"

        hblock_2 = yield self.env.process(self.count_votes("reduction_2", T_FRACTION, TAU_STEP,
                                    LAMBDA_BLOCK + LAMBDA_PROPOSER))

        if not hblock_2:
            return empty_block 

        return hblock_2

    def committee_vote(self, step, tau, hblock):
        """
        Verifiy if user is a committee member.
        
        Arguments:
        step   -- Name of the step eg. Reduction_1
        tau    -- expected number of committee members
        hblock -- Highest priority block

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """
        seed = vrf_seed(self.last_block_hash, self.round, step)
        j, vrf_hash = sortition(self.private_key, seed, TAU_STEP,
                                self.stake, self.total_stake)
        stake_subuser[self.stake] += j
        print("Committee Vote Node {}, Round {}, Step {}, subusers {}".format(self.node_id, self.round, step, j))
        if j > 0:
            payload = {
                        "round": self.round,
                        "step": step,
                        "vrf_hash": vrf_hash,
                        "j": j,
                        "prev_block_hash": self.last_block_hash,
                        "block": hblock,
                        "stake": self.stake
                      }
            
            # signature = self.signPayload(str(payload)).hex()
            signature = random.getrandbits(1000)

            message = {
                        "public_key": self.public_key,
                        "payload": payload,
                        "signature": signature
                      }

            self.message_generator(self.broadcastpipe_committee, message)
        # else:
        #     print("Node : {} committee_vote: not committee member".format(self.node_id))

    def dummy_timeout(self, env, wait_time):
        yield env.timeout(wait_time)
        return wait_time

    def count_votes(self, step, majority_frac, tau, wait_time):
        """
        Performs Reduction.

        Arguments:
        step          -- Name of the step eg. Reduction_1
        majority_frac -- fraction of votes for majority
        tau           -- expected number of committee members
        wait_time     -- time to wait for block proposals, if no proposals
                         recieved vote for empty block.

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """
        yield self.env.timeout(wait_time)
        count = {}  # count votes Dictionary[Block, votes]
        voters = set()  # set of voters Set[public key]
        blockcache = {}
        chosen_block = None
        messages = self.committeeBlockQueue_bc
        # self.committeeBlockQueue_bc = []

        # TODO: Discuss how to put delay. Followup from reduction function,
        #       search "where_timeout".

        for msg in messages:  # use this if all messages are available

            if not ((msg["payload"]["round"] == self.round) and
                    (msg["payload"]["step"] == step)):
                # print("count_votes: message skipped due to different rounds")
                continue

            votes, block, sorthash = self.process_message(step, TAU_STEP, msg)
            block_hash = hash_a_block(block)
            blockcache[block_hash] = block
            # check if voter already voted or zero votes(invalid message)
            if (votes == 0) or (sorthash["user_pk"] in voters):
                print("node.count_votes: default reply or zero votes")
                continue

            voters.add(sorthash["user_pk"])

            if block_hash in count:
                count[block_hash] += votes
            else:
                count[block_hash] = votes

            if count[block_hash] > majority_frac * tau:
                chosen_block = blockcache[block_hash]
        print("=== Votes received ===\n", count)
        # if not chosen_block:
        #     print("count_votes: no block selected")
        return chosen_block

    def process_message(self, step, tau, hblock_gossip_msg):
        # TODO: Fix verfiy sortition of another user.
        """
        Check validity of message and Return parsed values.

        Arguments:
        step              -- Name of the step eg. Reduction_1
        tau               -- expected number of committee members
        hblock_gossip_msg -- gossip messages from committee_vote

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """

        default_reply = 0, None, None  # reply in case of errors
        msg = hblock_gossip_msg  # rename for comfort

        # if not validate_signature(msg["public_key"],
        #                           str(msg["payload"]),
        #                           msg["signature"]):
        #     print("node.process_message: signature verify failed")
        #     return default_reply

        if msg["payload"]["prev_block_hash"] != self.last_block_hash:
            print("node.process_message: last block hash not match")
            return default_reply

        # TODO: implement verify sortition function
        seed = vrf_seed(self.last_block_hash, self.round, step)
        # subusers = verify_sort(msg["public_key"],
        #                        msg["payload"]["vrf_hash"],
        #                        seed,
        #                        TAU_STEP,
        #                        msg["payload"]["stake"],
        #                        self.total_stake)
        subusers = msg["payload"]["j"]
        
        if not subusers:
            # print("node.process_message: no sub users")
            return default_reply

        # TODO: Fix accorinding to message attributes
        votes = subusers  # j from sortition function
        block = msg["payload"]["block"]     # block
        
        sorthash = {}       # sortition details
        sorthash["user_pk"] = msg["public_key"]
        sorthash["subusers"] = subusers
        sorthash["vrf_hash"] = msg["payload"]["vrf_hash"]
        
        return votes, block, sorthash
    
    def binary_ba_star(self, block):
        """
        Reach consensus on a given block or empty block.

        Arguments:
        block -- block selected from reduction step

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """

        # Sir said to start at 3. Algorithm starts at 1
        # TODO: Discuss steps to be string or integer!
        step = 3
        r = block
        # FIXME: Why empty block require step & vrf_hash??
        empty_block = self.empty_block
        
        while step < MAX_STEPS:
            self.committee_vote(str(step), TAU_STEP, r)

            r = yield self.env.process(self.count_votes(str(step), T_FRACTION, TAU_STEP,
                                 LAMBDA_BLOCK + LAMBDA_PROPOSER))
            
            if not r:
                r = block
            elif r != empty_block :
                # TODO: Comfirm understanding.
                for i in range(step+1, step+4):
                    self.committee_vote(str(i), TAU_STEP, r)
                
                # TODO: Discuss Value of i = 3 or 1
                # TODO: Discuss why TAU_final different
                if step == 3:
                    self.committee_vote("final", TAU_STEP, r)
                return r
            
            step += 1

            self.committee_vote(str(step), TAU_STEP, r)

            r = yield self.env.process(self.count_votes(str(step), T_FRACTION, TAU_STEP,
                                 LAMBDA_BLOCK + LAMBDA_PROPOSER))
            
            if not r:
                r = empty_block
            elif r == empty_block:
                for i in range(step+1, step+4):
                    self.committee_vote(str(i), TAU_STEP, r)
                
                return r
            
            step += 1
            
            self.committee_vote(str(step), TAU_STEP, r)

            r = yield self.env.process(self.count_votes(str(step), T_FRACTION, TAU_STEP,
                                 LAMBDA_BLOCK + LAMBDA_PROPOSER))
            
            if not r:
                if self.common_coin(str(step), TAU) == 0:
                    r = block
                else:
                    r = empty_block

            step += 1
        
        print("node.binary_ba_star: hanging forever")
        self.hangforever()
    
    def hangforever(self):
        error_msg = "Node #" + str(self.node_id) + ": Hanged forever"
        print(error_msg)
        while True:
            """yo! yo! honey singh"""
            pass

    def common_coin(self, step, tau):
        """
        Compute common coin of all users

        Arguments:
        step              -- Name of the step eg. Reduction_1
        tau               -- expected number of committee members

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """
        # 256 is the length of sha256
        minhash = 2 ** 256

        messages = self.committeeBlockQueue_bc
        self.committeeBlockQueue_bc = []

        for msg in messages:
            votes, value, sorthash = self.process_message(step, TAU_STEP, msg)
            for i in range(1, votes):
                hash_subuser = str(sorthash["vrf_hash"]) + str(i)
                h = hashlib.sha256(hash_subuser.encode()).hexdigest()
                h = int(h, 16)
                if(h < minhash):
                    minhash = h
        
        return minhash % 2

    def ba_star(self, block):
        """
        Agreement protocol. Base function

        Arguments:
        block -- hash of highest priority block
        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """

        hblock = yield self.env.process(self.reduction(block))
        hblock_star = yield self.env.process(self.binary_ba_star(hblock))

        r = yield self.env.process(self.count_votes("final", T_FRACTION, TAU_STEP,
                             LAMBDA_BLOCK + LAMBDA_PROPOSER))
        
        if hblock_star == r:
            # TODO: Adjust block chain to handle tentative and final block
            return "final", hblock_star
        
        else:
            return "tentative", hblock_star
        
    def get_hblock(self, clear=True):
        """
        Return highest priority block from blockcache
        Highest priority block is the block with lowest priority

        Arguments:
        clear -- whether clear blockcache or not

        Hidden Arguments:
        blockcache -- Blockchain, state of ledger
        """
        cache = self.blockcache_bc
        if clear:
            self.blockcache_bc = []
        
        if cache:
            minblock = cache[0]
            for block in cache:
                if int(minblock["payload"], 16) < int(block["payload"], 16):
                    minblock = block

            return minblock

        return self.empty_block

    @property
    def last_block(self):
        """Return last block of blockchain."""
        return self.blockchain[-1]
    
    @property
    def last_block_hash(self):
        """Return hash of last block of blockchain."""
        return hashlib.sha256(str(self.last_block).encode()).hexdigest()
    
    @property
    def empty_block_hash(self):
        """
        Returns hash of emptyblock for consensus

        Hidden Arguments:
        last_block_hash -- hash of last block of blockchain
        round           -- round number
        """
        msg = {
            "hash_prev_block": self.last_block_hash,
            # TODO: Check whether round number is required
            "round" : self.round,
            "payload" : "Empty",
        }

        return hashlib.sha256(str(msg).encode()).hexdigest()

    @property
    def empty_block(self):
        """
        Returns emptyblock for consensus

        Hidden Arguments:
        last_block_hash -- hash of last block of blockchain
        round           -- round number
        """
        msg = {
            "hash_prev_block": self.last_block_hash,
            # TODO: Check whether round number is required
            "round" : self.round,
            "payload" : "Empty",
        }

        return msg

    def run_ba_star(self):
        """BA_Star driver."""
        # print("node.run_ba_star: hello")
        block = make_block_from_dict(self.get_hblock())
        # print("Node", self.node_id, "hpriorityblock:", block)
        state, block = yield self.env.process(self.ba_star(block))
        print("Node", self.node_id, "consensus_block:", block)
        
        # print(self.ba_star(block_hash))
        # print("state:",
        #       state,
        #       "\nblock:",
        #       block)
        
        #TODO: remove this and find some way to add actual blocks
        self.blockchain.append(block)
        
        self.round += 1
        self.committeeBlockQueue_bc = []
