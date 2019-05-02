import simpy
import random
SIM_TIME = 10
RANDOM_SEED = 13
class BroadcastPipe(object):
    def __init__(self, env, capacity=simpy.core.Infinity):
        self.env = env
        self.capacity = capacity
        self.pipes = []

    def put(self, value):
        if not self.pipes:
            raise RuntimeError('There are no output pipes.')
        events = [store.put(value) for store in self.pipes]
        return self.env.all_of(events)  # Condition event for all "events"

    def get_output_conn(self):

        pipe = simpy.Store(self.env, capacity=self.capacity)
        self.pipes.append(pipe)
        return pipe
        
def message_generator(name, env, out_pipe):
    while True:
        # wait for next transmission
        yield env.timeout(random.randint(6, 10))

        msg = (env.now, '%s says hello at %d' % (name, env.now))
        out_pipe.put(msg)


def message_consumer(name, env, in_pipe):
    """A process which consumes messages."""
    while True:
        msg = yield in_pipe.get()
        print('at time %d: %s received message: %s.' %
              (env.now, name, msg))

        # Process does some other work, which may result in missing messages
        # yield env.timeout(random.randint(6, 100))


# Setup and start the simulation
# print('Process communication')
# random.seed(RANDOM_SEED)
# env = simpy.Environment()

# For one-to-one or many-to-one type pipes, use Store
# pipe = simpy.Store(env)
# env.process(message_generator('Generator A', env, pipe))
# env.process(message_consumer('Consumer A', env, pipe))

# print('\nOne-to-one pipe communication\n')
# env.run(until=SIM_TIME)

# For one-to many use BroadcastPipe
# (Note: could also be used for one-to-one,many-to-one or many-to-many)
# env = simpy.Environment()
# bc_pipe = BroadcastPipe(env)



# env.process(message_generator('Generator A', env, bc_pipe))
# env.process(message_generator('Generator X', env, bc_pipe))

# env.process(message_consumer('Consumer B', env, bc_pipe.get_output_conn()))
# env.process(message_consumer('Consumer C', env, bc_pipe.get_output_conn()))


# print('\nOne-to-many pipe communication\n')
# env.run(until=SIM_TIME)