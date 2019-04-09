import random

def prg(seed):
    random.seed(seed)
    return str(random.getrandbits(256))

def concatenate(*arg):
	concat_str = ""
	for i in range(0,len(arg)):
		concat_str = concat_str + arg[i]