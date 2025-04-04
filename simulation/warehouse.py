import simpy as sp 
import statistics as st


class Warehouse:
    def __init__(self,env, consumption_rate, consumption_interval, init_rop, init_level=0, init_order_quantity=5 ):
        self.inventory = sp.Container(env, init=init_level)
        self.rop = init_rop
        self.monitor_proc = env.process(self.monitor_inventory(env))
        self.consume_proc = env.process(self.consume_inventory(env))
        self.consumption_rate = consumption_rate
        self.consumption_interval = consumption_interval
        self.order_quantity = init_order_quantity
        self.wait_for_order = False
        self.past_order_data = []

    def monitor_inventory(self, env):
        while True:
            if self.inventory.level <= self.rop and self.wait_for_order==False:
                print(f'Need to reorder at {env.now}')
                #todo add reorder functionality
                self.wait_for_order = True
                env.process(self.place_order(env))
            yield env.timeout(1)
    
    def update_inventory(self, env, incoming_goods):
        print(f"incoming goods at {env.now}")
        self.inventory.put(incoming_goods)

    def consume_inventory(self, env):
        while True:
            if self.inventory.level >= self.consumption_rate:
                print(f'consuming {self.consumption_rate} goods at {env.now}')
                yield self.inventory.get(self.consumption_rate)
                yield env.timeout(self.consumption_interval)
            else: 
                print(f'not enough inventory at {env.now}')
                yield env.timeout(1)

    def place_order(self, env):
        print("generate order")
        order = []
        order_placed= env.now
        for i in range(self.order_quantity):
            yield env.timeout(1)
            self.update_inventory(env, 1)
            order.append(env.now - order_placed)
        
        self.evaluate_order(order, "order_completion")
        self.update_rop_and_roq("singular")
        self.wait_for_order = False

    def evaluate_order(self,order,kpi):
        if kpi == "order_completion":
            order_performance = order[-1]
        self.past_order_data.append(order_performance)
        return True
    
    def update_rop_and_roq(self, kpi_type):
        if kpi_type == "singular":
            self.roq = st.mean(self.past_order_data) * (self.consumption_rate / self.consumption_interval)
            self.rop = 2 * self.roq

env = sp.Environment()
warehouse = Warehouse(env, consumption_interval=5, consumption_rate=5, init_rop=5, init_level=10)
env.run(until=22)
