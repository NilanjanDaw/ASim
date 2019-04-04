import ecdsa
from random import randint
from algorand import prg
import hashlib
import math

class Node:
    def __init__(self):
        genesis_string = "We are building the best Algorand Discrete Event Simulator"
        self.private_key = None
        self.public_key = None
        self.stake = randint(1, 50)
        self.blockchain = []
        self.generateCryptoKeys()
        genesis_block = self.formMessage(genesis_string)
        self.blockchain.append(genesis_block)
        print("Node has {} stake".format(self.stake))

    def generateCryptoKeys(self):
        self.private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        self.public_key = self.public_key.to_pem()
        self.private_key = self.private_key.to_pem()

        # print(self.public_key, self.private_key)

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
        print("last block: ", self.blockchain[-1])
        vrf_hash = self.vrf(self.blockchain[-1], 1, 1)
        print("vrf_hash", vrf_hash)
        threshold = int(vrf_hash, 16) / (2 ** (len(vrf_hash) * 4))
        print("threshold: ", threshold)

        while not (self.binomial_sum(j, self.stake, p) <= threshold <= self.binomial_sum(j + 1, self.stake, p)):
            j += 1 # TODO: have a second look at the validity of this line (test corner cases)
            if j == self.stake:
                break
        
        print(j)
    
    def nCr(self, n, r):
        f = math.factorial
        return f(n) // f(r) // f(n-r)


    def binomial_sum(self, j, w, p):
        sum = 0
        for k in range(0, j):
            sum += self.nCr(w, k) * (p ** k) * ((1 - p) ** (w - k))
        print("summing for", j, "sum=", sum)
        return sum

node = Node()

print(node.validatePayload(node.blockchain[0]))
node.sortition(20, 100)