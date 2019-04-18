import ecdsa
import network
from random import randint
from helper import prg, concatenate
import hashlib
import math



# Constants
# Expected committee size
TAU = 20

# Majority fraction of votes for BA*, T_FRACTION > 2/3(0.666....)
T_FRACTION = 68/100

# (milliseconds), Wait for this time to listen to priorities broadcast
LAMBDA_PROPOSER = 3000

# (milliseconds), Wait for LAMBDA_PROPOSER + LAMBDA_BLOCK = 33seconds to get a
# block proposal from highest priority node else commit for empty block
LAMBDA_BLOCK = 30000


class Node:
    def __init__(self, node_id, env, network_delay, bc_pipe):
        genesis_string = "We are building the best Algorand Discrete Event Simulator"
        self.node_id = node_id
        self.private_key = None
        self.public_key = None
        self.round = 0
        self.stake = randint(1, 50)
        self.cable = network.Network(env, network_delay)
        self.gossip_block = None
        self.neighbourList = []
        self.blockchain = []
        self.blockcache = []
        self.blockcache_bc = []
        self.broadcastpipe = bc_pipe #same pipe for all senders
        self.env = env
        self.generateCryptoKeys()
        genesis_block = self.formMessage(genesis_string)
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
        for x in range(neighbour_count):
            self.neighbourList.append(randint(0, node_count - 1))
        
        print("Node {} neighbour list".format(self.node_id), self.neighbourList)


    def signPayload(self, payload):
        sk = ecdsa.SigningKey.from_pem(self.private_key) 
        signature = sk.sign(str.encode(payload))
        return signature
    
    def formMessage(self, payload):
        msg = {
            "payload": payload,
            "public_key": self.public_key,
            "signature": self.signPayload(payload).hex()
        }
        return msg
    
    def validatePayload(self, payload):
        verifying_key = ecdsa.VerifyingKey.from_pem(payload['public_key'])
        return verifying_key.verify(bytes.fromhex(payload["signature"]), payload["payload"].encode())
    
    def vrf(self, previous_block, round_number, step_number):
        
        seed = hashlib.sha256(str(previous_block).encode()).hexdigest() + str(round_number) + str(step_number)
        # print(seed)
        vrf_signature = ecdsa.SigningKey.from_pem(self.private_key).sign(prg(seed).encode()).hex()
        return vrf_signature
    
    #TODO: check validitity of this function
    def sortition(self, tau, total_stake):
        p = tau / total_stake
        j = 0
        # print("last block: ", self.blockchain[-1])
        vrf_hash = self.vrf(self.blockchain[-1], self.round, 0) #TODO: vary round and step
        # print("vrf_hash", vrf_hash)
        threshold = int(vrf_hash, 16) / (2 ** (len(vrf_hash) * 4))
        # print("threshold: ", threshold)

        while not (self.binomialSum(j, self.stake, p) <= threshold <= self.binomialSum(j + 1, self.stake, p)):
            j += 1 # TODO: have a second look at the validity of this line (test corner cases)
            if j == self.stake:
                break
        
        # print(j)
        return j, vrf_hash
    
    def priorityProposal(self, step):
        j, vrf_hash = self.sortition(TAU, 300)
        if j > 0:
            max_priority, subuser_index = self.getPriority(vrf_hash, j)
            gossip_message = self.generateGossipMessage(vrf_hash, subuser_index, max_priority)
            # print("Block ready to be gossiped:", gossip_message)
            return gossip_message
        else:
            print("Node not selected for this round")
            return None

    def blockProposal(self):
        print("block proposal started")
        # "<SHA256(Previous block)||256 bit long random string || Node’s Priority payload>"
        priority = min (block["priority"] for block in self.blockcache)
        message = {
            "hash_prev_block": hashlib.sha256(str(self.blockchain[-1]).encode()).hexdigest(), 
            "rand_str_256": prg(13), 
            # check if it is correct
            "priority_payload": priority,

        }
        self.message_generator(self.broadcastpipe, message)
        print("block proposal done")
    
    def message_generator(self, out_pipe, message):
        # This is the transmission delay but set it according to message length
        # yield env.timeout(random.randint(6, 10))
        # time = int(len(str(message))/32) # 16 char per sec transmission speed
        # print("time calculated using bandwidth:",time,message,len(str(message)))
        # yield env.timeout(time)
        out_pipe.put(message)


    def message_consumer(self, in_pipe):
        while True:
            msg = yield in_pipe.get()
            print("msg receive--------------------------------")
            self.blockcache_bc.append(msg)
            print('received message: %s.' %(msg))


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
                self.blockcache.append(block)
    
    def nCr(self, n, r):
        f = math.factorial
        return f(n) // f(r) // f(n-r)

    def binomialSum(self, j, w, p):
        sum = 0
        for k in range(0, j):
            sum += self.nCr(w, k) * (p ** k) * ((1 - p) ** (w - k))
        # print("summing for", j, "sum=", sum)
        return sum

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
        j, vrf_hash = self.sortition(TAU, 300)
        # change it to json format
        message = {
            "hash_prev_block": hashlib.sha256(self.blockchain[-1]),
            "round" : self.round,
            "step" : self.step,
            "msg" : "Empty", 
            "vrf_hash" : vrf_hash,
        }
        return message

    def checkLeader(self):
        if self.gossip_block is not None:
            if len(self.blockcache) > 0:
                priority = min (block["priority"] for block in self.blockcache)
                if self.gossip_block["priority"] < priority:
                    print("Node {} leader".format(self.node_id))
                    return True
            else:
                print("blockcache empty")
        else:
            print("Node {} is not a proposer for this round".format(self.node_id))
        
        return False

    def committeeSelection(self):
        seed = hashlib.sha256(self.blockchain[-1]) + self.round + "1"
        value = prg(seed)
        j, vrf_hash = self.sortition(TAU, 300)
        # do cryptographic sortition , use tau_step
        # return True/False based on selection
        if j > 0:
            return True
        return False 

    def reduction(self, hblock):
        """
        Performs Reduction.

        Arguments:
        hblock -- Highest priority block

        Hidden Arguments:
        ctx   -- Blockchain, state of ledger
        round -- round number
        """

        # TODO: Get highest priority block

        self.committee_vote("Reduction_1", TAU, hblock)

        # TODO: Search tag "where_timeout".
        #       Possible timeout needed, my doubt is where is it needed. This
        #       node waits for lamda_block + lamda_step seconds before
        #       counting for votes. Should timeout here or inside count_vote
        #       function. Add timeout of lamda_block + lamda_step

        hblock_1 = self.count_votes("Reduction_1", T_FRACTION, TAU,
                                 LAMBDA_BLOCK + LAMBDA_PROPOSER)

        # FIXME: Why empty block require step & vrf_hash??
        empty_block = self.generateEmptyBlock(hashlib.sha256(str(self.blockchain[-1]).encode()).hexdigest(),
                                              self.round,
                                              "Reduction_2",
                                              self.sortition(TAU, 300)[1])
        if not hblock_1:
            self.committee_vote("Reduction_2", TAU, empty_block)
        else:
            self.committee_vote("Reduction_2", TAU, hblock_1)

        # TODO: Same issue as search tag "where_timeout"
        hblock_2 = self.count_votes("Reduction_1", T_FRACTION, TAU,
                                    LAMBDA_BLOCK + LAMBDA_PROPOSER)

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

        # TODO: Proper sortition verification

        # FIXME: Select one of the below if statements
        # j, vrf_hash = self.sortition(tau, 300)
        # if j > 0:
        #     # TODO: search tag "vote_gossip_message"
        #     #       gossip<user.pk,
        #     #               signedmessage<self.round,
        #     #                             self.step,
        #     #                             vrf_hash,
        #     #                             j,
        #     #                             sortition_proof,
        #     #                             hash(self.blockchain[-1]),
        #     #                             hblock
        #     #                            >
        #     #              >
        #     # Probably use "formmessage" or whatever.
        #     # Make compatible with self.validatePayload
        #     pass
        
        # if self.committeeSelection():
        #     # TODO: search tag "vote_gossip_message"
        #     #       gossip<user.pk,
        #     #               signedmessage<self.round,
        #     #                             self.step,
        #     #                             hash(self.blockchain[-1]),
        #     #                             hblock
        #     #                            >
        #     #              >
        #     # Probably use "formmessage" or whatever.
        #     # Make compatible with self.validatePayload
        #     pass

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

        # TODO: Check if following line gets the current time properly
        # TODO: Dicuss timeout. start varible is required for it in algo 5 of
        #       paper search "where_timeout".
        # start: int = self.env.now

        count = {}  # count votes Dictionary[Block, votes]
        voters = set()  # set of voters Set[public key]

        # TODO: Get messages vote messages from network. I didn't send
        #       messages. We have to add that functionality. To find where the
        #       messages enter the network serach "vote_gossip_message"
        messages = []

        # TODO: Discuss how to put delay. Followup from reduction function,
        #       search "where_timeout".

        # TODO: Select appropriate loop
        # While True:  # use this if all messages are not available at time
        #              # this function runs
        #   msg = messages.get() or messages.next() or whatever
        for msg in messages:  # use this if all messages are available

            votes, block, public_key = self.process_message(TAU, msg)

            # check if voter already voted or zero votes(invalid message)
            if (public_key in voters) or (votes == 0):
                continue

            voters.add(public_key)

            if block in count:
                count[block] += votes
            else:
                count[block] = votes

            if count[block] > majority_frac * tau:
                return block
        
        # TODO: Fix according to the network overlay chosen. This statement is
        #       for no messages received case
        if not messages:
            return None

    def process_message(self, step, tau, hblock_gossip_msg):
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

        # TODO: Fix according to message attributes
        if not (msg["step"] == step and
                msg["round"] == self.round):
            return default_reply

        # TODO: Verify compliance with self.validatePayload(msg)
        if not self.validatePayload(msg):
            return default_reply

        # TODO: Fix according to message attributes
        if msg["hash_prev_block"] != hashlib.sha256(str(self.blockchain[-1]).encode()).hexdigest():
            return default_reply

        # TODO: Fix accorinding to message attributes
        votes = msg["subvoters"]  # j from sortition function
        pk = msg["user_pk"]       # public key of message sender
        block = msg["hblock"]     # block

        return votes, pk, block