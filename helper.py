import random
import ecdsa
import hashlib
import math

stake_subuser = [0] * 50

def prg(seed):
    random.seed(seed)
    return str(random.getrandbits(256))


def vrf(private_key, seed):
    vrf_signature = ecdsa.SigningKey.from_pem(private_key).sign(prg(seed).encode()).hex()
    return vrf_signature


def verify_vrf(public_key, vrf_signature, seed):
    public_key = ecdsa.VerifyingKey.from_pem(public_key)
    return public_key.verify(bytes.fromhex(vrf_signature), prg(seed).encode())


def vrf_seed(prev_block_hash, round_num, step):
    seed = hashlib.sha256((prev_block_hash + str(round_num) + str(step)).encode()).hexdigest()
    return prg(seed)


def nCr(n, r):
    f = math.factorial
    return f(n) // f(r) // f(n-r)


def binomialSum(j, w, p):
    sum_ = 0
    for k in range(0, j):
        sum_ += nCr(w, k) * (p ** k) * ((1 - p) ** (w - k))
    # print("summing for", j, "sum=", sum)
    return sum_


def sortition(private_key, seed, tau, stake, total_stake):
    vrf_hash = vrf(private_key, seed)
    p = tau / total_stake
    j = 0

    threshold = int(vrf_hash, 16) / (2 ** (len(vrf_hash) * 4))
    # print("threshold: ", threshold)

    while not (binomialSum(j, stake, p) <= threshold <= binomialSum(j + 1, stake, p)):
        j += 1
        if j == stake:
            break

    # print(j)
    return j, vrf_hash


def verify_sort(public_key, vrf_hash, seed, tau, stake, total_stake):

    # if not verify_vrf(public_key, vrf_hash, seed):
    #     return 0

    p = tau / total_stake
    j = 0
    threshold = int(vrf_hash, 16) / (2 ** (len(vrf_hash) * 4))
    # print("threshold: ", threshold)

    while not (binomialSum(j, stake, p) <= threshold <= binomialSum(j + 1, stake, p)):
        j += 1
        if j == stake:
            break

    # print(j)
    return j


def validate_signature(public_key, message, signature):
    public_key = ecdsa.VerifyingKey.from_pem(public_key)
    return public_key.verify(bytes.fromhex(signature), message.encode())


def hash_a_block(block):
    block = make_block_from_dict(block)
    return hashlib.sha256(str(block).encode()).hexdigest()


def make_block_from_dict(msg):
    if (("hash_prev_block" in msg) and
       ("payload" in msg) and
       ("round" in msg)):
        block = {
                    "hash_prev_block": msg["hash_prev_block"],
                    "payload": msg["payload"],
                    "round": msg["round"]
                }
        return block

    raise KeyError("All block components not found")



def byz_make_block_from_dict(msg):
    if (("hash_prev_block" in msg) and
       ("payload" in msg) and
       ("round" in msg)):
        block = {
                    "hash_prev_block": msg["hash_prev_block"],
                    "payload": msg["payload"],
                    "round": msg["round"],
                    "is_adversary":True,
                }
        return block

    raise KeyError("All block components not found")


# seed = "lol"

# private_key = ecdsa.SigningKey.generate()
# public_key = private_key.get_verifying_key()
# private_key = private_key.to_pem()
# public_key = public_key.to_pem()

# x,y = sortition(private_key, seed, 10, 100, 100)
# print("Signature: ", x, y)
# print(verify_sort(public_key, y, seed, 10, 100, 100))
