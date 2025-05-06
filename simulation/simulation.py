import numpy as np
import statistics as st
from datetime import datetime, date, time, timedelta
from warehouse import Warehouse
from order import Order, Shipment
import matplotlib.pyplot as plt
from OCEL_FormatGenerator import generate_ocel_event_log, adjust_to_weekday
import pm4py as pm 
import time

class Simulation:
    def __init__(
        self, config:dict ):
        keys= ['start_date', 'days', 'warehouse', 'seed', 'mean_daily_demand','std_daily_demand','delivery_func', 'delivery_split_centre', 'delivery_split_std', 'verbose']
        for key in keys:
            setattr(self, key, config.get(key))
        # self.start_date = start_date
        # self.current_date = start_date
        # self.days = days
        # self.warehouse = warehouse
        # self.seed = seed
        # self.mean_daily_demand = mean_daily_demand
        # self.std_daily_demand = std_daily_demand
        # self.delivery_func = delivery_func
        # self.delivery_split_centre = delivery_split_centre
        # self.delivery_split_std = delivery_split_std 
        
        self.current_date = self.start_date
        self.shipment_schedule = []
        self.inventory_history_on_hand = []
        self.inventory_history_in_transit = []
        self.inventory_history_total = []
        self.past_rops=[]
        self.past_eoqs=[]
        self.past_safety_stock=[]
        self.backorders = 0
        self.fulfilled_demand = 0
        self.total_demand = 0
        self.out_of_stock = 0
        self.total_holding_costs = 0

    
    def simulate_order(self, order):
        if self.verbose:
            print(f"generate order {order.id} with quantity {order.quantity}")
        delivery_days = max(1, int(np.random.normal(self.delivery_split_centre, self.delivery_split_std)))
        generate_ocel_event_log(start_date=self.current_date, amount=order.quantity, func=self.delivery_func, iteration=order.id, del_days=delivery_days)
        
        date_str = adjust_to_weekday(self.current_date).strftime("%Y-%m-%d")
        #time.sleep(10)
        ocel = pm.read_ocel2_json(f"Output/OrderProcess_{date_str}.json")
        filtered_ocel = pm.filter_ocel_event_attribute(ocel,'ocel:activity',['Deliver Package'])

        relations_with_timestamps = filtered_ocel.events.merge(filtered_ocel.relations, on="ocel:eid", ).drop(columns=['company',
            'payment_method', 'checker', 'spliter', 'picker', 'packer', 'storer','loader', 'logistics_company', 'ocel:activity_y',
            'ocel:timestamp_y', 'ocel:type', 'ocel:qualifier'],
            errors="ignore")
        shipments_with_time_and_qty = relations_with_timestamps.merge(filtered_ocel.objects, on="ocel:oid")

        for id,shipment in shipments_with_time_and_qty.iterrows():
            self.shipment_schedule.append(Shipment(ship_id=id, order_id=order.id, quantity=shipment["amount"], delivery_date=shipment["ocel:timestamp_x"].to_pydatetime()))
    
    def simulate_deliveries(self):
        # 1. receive any delivereies
            for shipment in self.shipment_schedule[:]:
                if shipment.delivery_date.date() == self.current_date.date():
                    self.warehouse.receive_shipment(shipment=shipment, date=self.current_date)

                    self.shipment_schedule.remove(shipment)

    def simulate_demand(self):
        demand_today = max(0, int(np.random.normal(self.mean_daily_demand, self.std_daily_demand))) 
        fulfilled_demand_today, backorders_today = self.warehouse.consume_inventory(self.current_date, demand_today)
        
        order = self.warehouse.monitor_inventory(self.current_date)
        if order:
            self.simulate_order(order)
        
        return demand_today, fulfilled_demand_today, backorders_today       
    
    def run(self):
        np.random.seed(self.seed)
        if self.verbose:
            print(f'start sim at {self.current_date}')
        for day in range(self.days):
            self.current_date = self.start_date + timedelta(days=day)

            self.simulate_deliveries()
            demand_today, fulfilled_demand_today, backorders_today = self.simulate_demand()
            
            self.total_demand += demand_today
            self.fulfilled_demand += fulfilled_demand_today
            self.backorders += backorders_today  
            self.total_holding_costs += self.warehouse.inventory * (self.warehouse.holding_cost/365)

            self.past_safety_stock.append(self.warehouse.safety_stock)
            self.past_rops.append(self.warehouse.rop)
            self.past_eoqs.append(self.warehouse.eoq)

            self.inventory_history_on_hand.append(self.warehouse.inventory)
            self.inventory_history_in_transit.append(self.warehouse.inventory_in_transit)
            self.inventory_history_total.append(self.warehouse.inventory + self.warehouse.inventory_in_transit)

            if self.warehouse.inventory == 0:
                self.out_of_stock += 1

    def evaluate(self,report=False):
        # --- Results ---
        self.results = {
            'service_level' : self.fulfilled_demand / self.total_demand,
            'total_demand' : self.total_demand,
            'fulfilled_demand' : self.fulfilled_demand,
            'backorders' : self.backorders,
            'stock_outs' : self.out_of_stock,
            'orders_placed' : self.warehouse.orders_placed,
            'total_holding_costs' : self.total_holding_costs,
            'total_inventory_on_hand' : sum(self.inventory_history_on_hand),
            'mean_lead_time' : st.mean(self.warehouse.order_performances),
            'mean_order_size' : st.mean(self.warehouse.order_sizes)
        }
        if report == True:
            for key, value in self.results.items():
                print(f"{key}: {value}")

        return self.results

    def visualize(self):
        # --- Visualization ---
        plt.figure(figsize=(12, 6))
        plt.plot(self.inventory_history_on_hand, label='Inventory On hand')
        #plt.plot(self.inventory_history_in_transit, label='Inventory in transit')
        plt.plot(self.inventory_history_total, label='Total Inventory')
        plt.plot(self.past_rops, color='r', linestyle='--', label='Reorder Point')
        plt.plot(self.past_eoqs, color='y', linestyle='--', label='EOQ')
        plt.plot(self.past_safety_stock, color='g', linestyle='--', label='safety stock')
        plt.title('Inventory Level Over Time')
        plt.xlabel('Day')
        plt.ylabel('Inventory')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
            

        