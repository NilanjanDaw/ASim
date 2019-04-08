import random

def prg(seed):
    random.seed(seed)
    return str(random.getrandbits(256))

