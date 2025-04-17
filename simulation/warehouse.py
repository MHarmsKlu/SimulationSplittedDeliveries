
import statistics as st
from order import Order 
import math


class Warehouse:
    def __init__(self, init_rop, init_eoq, order_base_cost, order_piece_cost, holding_cost, init_level, kpi ):
        self.inventory = init_level
        self.rop = init_rop
        self.eoq = init_eoq
        self.kpi = kpi
        self.wait_for_order = False
        self.open_orders = []
        self.order_performances = []
        self.past_demand = []
        self.past_eoqs = [init_eoq]
        self.order_base_cost = order_base_cost
        self.order_piece_cost = order_piece_cost
        self.holding_cost = holding_cost
        self.orders_placed = 0
    
    def monitor_inventory(self, date):
        if self.inventory <= self.rop and self.wait_for_order==False:
            print(f'Need to reorder at {date}')
            #todo add reorder functionality
            self.wait_for_order = True
            order = Order(id=self.orders_placed,  order_placed=date, quantity=self.eoq )
            self.open_orders.append(order)
            self.orders_placed += 1
            return self.inventory, order
        else:
            return self.inventory, False
    
    def consume_inventory(self, date, demand):
        self.past_demand.append(demand)
        backorders = 0
        fulfilled_demand = 0
        if self.inventory >= demand:
            print(f'consuming {demand} goods at {date}')
            self.inventory -= demand
            fulfilled_demand = demand
        else: 
            print(f'not enough inventory at {date}')
            fulfilled_demand = self.inventory
            backorders = demand - self.inventory
            self.inventory = 0
        return fulfilled_demand, backorders

    def receive_shipment(self, date, shipment):
        print(f"incoming {shipment.quantity} goods at {date}")
        for order in self.open_orders:
            if order.id == shipment.order_id:
                order.update(shipment)
                if order.complete:
                    self.evaluate_order(order)
        self.inventory += shipment.quantity
        return self.inventory

    def evaluate_order(self,order):
        if self.kpi == "order_completion":
            order_performance  = order.completed - order.placed
        
        # elif kpi == "effective_lt_per_good":
        #     weighted_times = []
        #     for partial in order:
        #         weighted_times.append(partial["time"] * partial["quantity"])
        #     order_performance = sum(weighted_times)/self.order_quantity
        
        self.open_orders.remove(order)
        self.order_performances.append(order_performance.days)
        self.update_rop()
        self.update_eoq()
        self.wait_for_order = False
    
    def update_eoq(self):
        mean_order_costs = self.order_base_cost + (self.order_piece_cost * st.mean(self.past_eoqs))
        self.past_eoqs.append(self.eoq)
        self.eoq =  int(math.sqrt((2*st.mean(self.past_demand)* mean_order_costs)/self.holding_cost))

    def update_rop(self):
        
        if self.kpi == "order_completion":
            self.rop = st.mean(self.order_performances) * st.mean(self.past_demand)
        # if kpi_type == "effective_lt_per_good":
        #     self.roq = st.mean(self.past_order_data) * (self.consumption_rate / self.consumption_interval)
        #     self.rop = 2 * self.roq
