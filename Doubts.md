# DOUBTS and Proposed Solutions
- SimPy : SimPy is an object-oriented, process-based discrete-event simulation library for Python.
Can we use this library?

- Network delays are fixed before simulation starts. Delays are sampled for each edge from normal distribution with mean 30ms and variance 64ms. Or is it a single sampled value for each edge?

- Internal Events like Verify Signature should be considered as events or not?
We think yes.

- A Single Process Model (no threads):
Our models will execute on sequential computers in a single process.

# State:
State of system at a particular time.
What should it be concretely?

# Event:
A rough view of how events should be classified:-
Action that changes the state of system like : 
Send message. 
Recieve message.
Verify block recieved.(Validate Sortition by each node)
Cast vote by one committee member.
and so on...
Is this correct?



Operation:
a sequence of activities that changes the state of the system

Simulation Time:
Every node(algorand node) will have its own clock. 
Say we want every node to wait for 3 seconds and then start operating on recieved blocks. Until these 3 seconds are finished, block proposers will execute their event of sending blocks to  other nodes and rest will work as relays. 
Should we consider an EVENT as:

<b> Node1 sending block to Node2 (both send and recieve) </b>

<b>Or Send and Recieve as different events? Here, Node1 will push block in the queue of Node2. And this is one event in simulation process. </b>

<b> While doing so, we'll decrement the clock-time of only the nodes which are involed in that Event. So here, Node1 and Node2 clock-time of 3 seconds will get decremented while other nodes will have their 3 seconds clock as it is. </b>



- Multi-threaded Model:
Use TCP and sockets. This we're not considering and it seems a wrong approach too. 







