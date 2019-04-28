import simpy
import numpy as np
SIM_DURATION = 100000
class Network(object):
    def __init__(self, env, delay):
        self.env = env
        self.delay = delay
        self.store = simpy.Store(env)

    def latency(self, value):
        yield self.env.timeout(self.delay)
        self.store.put(value)

    def put(self, value):
        self.env.process(self.latency(value))

    def get(self):
        return self.store.get()

def sender(env, cable):
    """A process which randomly generates messages."""
    while True:
        # wait for next transmission
        # TODO: Check if this timeout is required
        yield env.timeout(5000)
        cable.put('Sender sent this at %d' % env.now)


def receiver(env, cable):
    while True:
        # Get event for message pipe
        msg = yield cable.get()
        print('Received this at %d while %s' % (env.now, msg))


# Setup and start the simulation
# print('Event Latency')
# env = simpy.Environment()
# mu = 200
# signa = 400
# statistical_delay = max(0, np.random.normal(mu, signa, 1)[0])
# print(statistical_delay)
# cable = Network(env, statistical_delay)
# cable2 = Network(env, statistical_delay)
# env.process(sender(env, cable))
# env.process(sender(env, cable2))
# env.process(receiver(env, cable))
# env.process(receiver(env, cable2))
# env.run(until=SIM_DURATION)