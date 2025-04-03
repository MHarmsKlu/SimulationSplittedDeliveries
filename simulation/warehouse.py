import simpy as sp 


class Warehouse:
    def __init__(self,env, consumation_rate, consumation_interval, bsl, init_capcity=0 ):
        self.inventory = sp.Container(env, init=init_capcity)
        self.bsl = bsl
        self.monitor_proc = env.process(self.monitor_inventory(env))
        self.consume_proc = env.process(self.consume_inventory(env))
        self.consumation_rate = consumation_rate
        self.consumation_interval = consumation_interval

    def monitor_inventory(self, env):
        while True:
            if self.inventory.level <= self.bsl:
                print(f'Need to reorder at {env.now}')
                #todo add reorder functionality
            yield env.timeout(1)
    
    def update_bsl(new_bsl):
        self.bsl = new_bsl
    
    def update_inventory(env, incoming_goods):
        yield self.inventory.put(incoming_goods)

    def consume_inventory(self, env):
        while True:
            if self.inventory.level >= self.consumation_rate:
                print(f'consuming {self.consumation_rate} goods at {env.now}')
                yield self.inventory.get(self.consumation_rate)
                yield env.timeout(self.consumation_interval)
            else: 
                print(f'not enough inventory at {env.now}')

env = sp.Environment()
warehouse = Warehouse(env, consumation_interval=5, consumation_rate=5, bsl=5)
env.run(until=22)
