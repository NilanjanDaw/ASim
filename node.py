import ecdsa
import network
from random import randint
from helper import prg
import hashlib
import math

class Node:
    def __init__(self, node_id, env, network_delay):
        genesis_string = "We are building the best Algorand Discrete Event Simulator"
        self.node_id = node_id
        self.private_key = None
        self.public_key = None
        self.round = 0
        self.stake = randint(1, 50)
        self.cable = network.Network(env, network_delay)
        self.neighbourList = []
        self.blockchain = []
        self.blockcache = []
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
        print(seed)
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
        print("threshold: ", threshold)

        while not (self.binomial_sum(j, self.stake, p) <= threshold <= self.binomial_sum(j + 1, self.stake, p)):
            j += 1 # TODO: have a second look at the validity of this line (test corner cases)
            if j == self.stake:
                break
        
        # print(j)
        return j, vrf_hash
    
    def block_proposal(self, step):
        j, vrf_hash = self.sortition(20, 300)
        if j > 0:
            max_priority, subuser_index = self.get_priority(vrf_hash, j)
            gossip_message = self.generateGossipMessage(vrf_hash, subuser_index, max_priority)
            print("Block ready to be gossiped:", gossip_message)
            return gossip_message
        else:
            print("Node not selected for this round")
    

    def get_priority(self, vrf_hash, subuser_count):
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
                print("{} received block {}".format(self.node_id, block))
                self.blockcache.append(block)
    
    def nCr(self, n, r):
        f = math.factorial
        return f(n) // f(r) // f(n-r)

    def binomial_sum(self, j, w, p):
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
    
    def checkLeader(self):
        pass


def start_simulation(env, node_list, node):
    
        print(node.validatePayload(node.blockchain[0]))
        while True:
            block = node.block_proposal(1)
            node.sendBlock(node_list, block)
            yield env.timeout(3000)
            node.checkLeader()

