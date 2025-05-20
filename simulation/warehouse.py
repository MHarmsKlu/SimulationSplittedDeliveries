
import statistics as st
from order import Order 
import math
from curve_fitting import fit_distribution


class Warehouse:
    def __init__(self, config:dict ):
        
        keys={'rop', 'eoq','z_score', 'order_base_cost', 'holding_cost', 'inventory', 'kpi', 'verbose'}
        # z-score based on idea that lead times are normal distributed
        for key in keys:
            setattr(self, key, config.get(key))
        
        self.inventory_in_transit = 0
        self.safety_stock =  0
        self.wait_for_order = False
        self.open_orders = []
        self.order_performances = []
        self.order_sizes = []
        self.past_demand = []
        self.orders_placed = 0
    
    def monitor_inventory(self, date):
        if self.inventory <= self.rop and self.wait_for_order==False:
            if self.verbose:
                print(f'Need to reorder at {date}')
            
            self.wait_for_order = True
            self.update_eoq()
            self.order_sizes.append(self.eoq)
            order = Order(id=self.orders_placed,  order_placed=date, quantity=self.eoq )
            self.open_orders.append(order)
            self.orders_placed += 1
            self.inventory_in_transit = order.quantity
            return order
        else:
            return False
    
    def consume_inventory(self, date, demand):
        self.past_demand.append(demand)
        backorders = 0
        fulfilled_demand = 0
        if self.inventory >= demand:
            #print(f'consuming {demand} goods at {date}')
            self.inventory -= demand
            fulfilled_demand = demand
        else: 
            #if self.verbose:
                #print(f'not enough inventory at {date}')
            fulfilled_demand = self.inventory
            backorders = demand - self.inventory
            self.inventory = 0
        return fulfilled_demand, backorders

    def receive_shipment(self, date, shipment):
        if self.verbose:
            print(f"incoming {shipment.quantity} goods at {date}")
        for order in self.open_orders:
            if order.id == shipment.order_id:
                order.update(shipment)
                if order.complete:
                    self.evaluate_order(order)
        self.inventory += shipment.quantity
        self.inventory_in_transit -= shipment.quantity
        return self.inventory

    def evaluate_order(self,order):
        if self.kpi == "order_completion":
            order_performance  = (order.completed.date() - order.placed.date()).days
        if self.kpi == "item_completion":
            shipment_performances = []
            for ship in order.shipments:
                shipment_performances.append((ship.delivery_date.date() - order.placed.date()).days )
            order_performance = st.mean(shipment_performances)
        if self.kpi == "item_distribution_mean":
            shipment_dates = []
            shipment_quantities = []
            for ship in order.shipments:
                shipment_dates.append((ship.delivery_date.date() - order.placed.date()).days )
                shipment_quantities.append(ship.quantity)
            order_performance = fit_distribution(shipment_dates,shipment_quantities)
        
        self.open_orders.remove(order)
        self.order_performances.append(order_performance)
        self.update_safety_stock()
        self.update_rop()
        self.update_eoq()
        self.wait_for_order = False

    def update_safety_stock(self):
        if len(self.order_performances) > 1:
            self.safety_stock = self.z_score * math.sqrt((st.mean(self.order_performances)* st.stdev(self.past_demand)**2) + (st.mean(self.past_demand)*st.stdev(self.order_performances)**2))
    
    def update_eoq(self):
        self.eoq =  int(math.sqrt((2*365*st.mean(self.past_demand)* self.order_base_cost)/self.holding_cost))

    def update_rop(self):
        if self.kpi == "order_completion":
            self.rop = (st.mean(self.order_performances) * st.mean(self.past_demand)) + self.safety_stock
        if self.kpi == "item_completion":
            self.rop = (st.mean(self.order_performances) * st.mean(self.past_demand)) + self.safety_stock
        if self.kpi == "item_distribution_mean":
            self.rop = (st.mean(self.order_performances) * st.mean(self.past_demand)) + self.safety_stock

