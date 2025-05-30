
import statistics as st
from order import Order 
import math
from curve_fitting import fit_distribution


class Warehouse_SKU:
    def __init__(self, config:dict ):
        
        keys={'id','rop', 'eoq','z_score', 'order_base_cost', 'holding_cost', 'inventory', 'kpi', 'verbose' }
        # z-score based on idea that lead times are normal distributed
        for key in keys:
            setattr(self, key, config.get(key))
        
        self.inventory_in_transit = 0
        self.safety_stock =  0
        self.wait_for_order = False
        self.order_performances = []
        self.order_sizes = []
        self.past_demand = []
        self.fulfilled_demand = 0
        self.backorders=0
        self.total_demand = 0
        self.out_of_stock = 0
        self.total_holding_costs = 0
       
    @property
    def current_holding_cost(self):
        return self.inventory * (self.holding_cost/365)
    
    def monitor_inventory(self):
        if self.inventory <= self.rop and self.wait_for_order==False:
            self.wait_for_order = True
            self.update_eoq()
            self.order_sizes.append(self.eoq)
            
            self.inventory_in_transit = self.eoq
            return self.eoq
        else:
            return False
    
    def consume_inventory(self, date, demand):
        self.past_demand.append(demand)
        backorders_today = 0
        fulfilled_demand_today = 0
        if self.inventory >= demand:
            #print(f'consuming {demand} goods at {date}')
            self.inventory -= demand
            fulfilled_demand_today = demand
        else: 
            #if self.verbose:
                #print(f'not enough inventory at {date}')
            fulfilled_demand_today = self.inventory
            backorders_today = demand - self.inventory
            self.inventory = 0
        
        self.total_demand += demand
        self.fulfilled_demand += fulfilled_demand_today
        self.backorders += backorders_today  
        self.total_holding_costs += self.current_holding_cost


        if self.inventory == 0:
            self.out_of_stock += 1
        return fulfilled_demand_today, backorders_today

    def receive_shipment(self, shipment,order_sku):
        if order_sku.complete:
            self.evaluate_order(order_sku)
        self.inventory += shipment.SKUs[self.id]
        self.inventory_in_transit -= shipment.SKUs[self.id]
        return self.inventory

    def evaluate_order(self,order_sku):
        if self.kpi == "order_completion":
            order_performance  = (order_sku.completed.date() - order_sku.placed.date()).days
        if self.kpi == "item_completion":
            shipment_performances = []
            for ship in order_sku.shipments:
                shipment_performances.append((ship.delivery_date.date() - order_sku.placed.date()).days )
            order_performance = st.mean(shipment_performances)
        if self.kpi == "item_distribution_mean":
            shipment_dates = []
            shipment_quantities = []
            for ship in order_sku.shipments:
                shipment_dates.append((ship.delivery_date.date() - order_sku.placed.date()).days )
                shipment_quantities.append(ship.quantity)
            order_performance = fit_distribution(shipment_dates,shipment_quantities)
        
        
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

class Warehouse:
    def __init__(self, SKU_configs ):
        self.open_orders=[]
        self.orders_placed = 0 
        self.SKUs = {}
        
        for con in SKU_configs:
            self.SKUs[con['id']]=Warehouse_SKU(con)
    @property             
    def inventory(self):
        inventory = 0
        for sku in self.SKUs.values():
            inventory += sku.inventory
        return inventory
    @property             
    def inventory_in_transit(self):
        inventory_in_transit = 0
        for sku in self.SKUs.values():
            inventory_in_transit += sku.inventory_in_transit
        if inventory_in_transit < 0:
            print("here")
        return inventory_in_transit
    
    @property
    def current_holding_cost(self):
        current_holding_cost = 0
        for sku in self.SKUs.values():
            current_holding_cost += sku.current_holding_cost
        return current_holding_cost


    def monitor_inventory(self, date):
        order_config = {}
        for sku_id,sku in self.SKUs.items():
            order_sku_config = sku.monitor_inventory()
            if order_sku_config:
                order_config[sku_id] = order_sku_config
        if len(order_config.values()) > 0:
            order = Order(id=self.orders_placed, order_placed=date,sku_configs=order_config)
            self.open_orders.append(order)
            self.orders_placed += 1
            return order
        else:
            return False

    def consume_inventory(self, date, demands):
        fulfilled_demand = 0
        backorders = 0
        for sku in demands.keys():
            sku_fulfilled, sku_backorders = self.SKUs[sku].consume_inventory(date, demands[sku])
            fulfilled_demand += sku_fulfilled
            backorders += sku_backorders
        return fulfilled_demand, backorders
    
    def receive_shipment(self, shipment):
        
        for order in self.open_orders:
            if order.id == shipment.order_id:
                order.update(shipment)
                for sku in shipment.SKUs.keys():
                    self.SKUs[sku].receive_shipment(shipment, order.SKUs[sku])
            if order.complete:
                self.open_orders.remove(order)
        return self.inventory

    #TODO add global statistics as property