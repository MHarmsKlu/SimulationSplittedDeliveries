import numpy as np
from datetime import datetime, date, time, timedelta
from warehouse import Warehouse
from order import Order, Shipment
import matplotlib.pyplot as plt

class Simulation:
    def __init__(
        self, start_date, days, warehouse, seed, mean_daily_demand,std_daily_demand ):
        
        self.start_date = start_date
        self.current_date = start_date
        self.days = days
        self.warehouse = warehouse
        self.seed = np.random.seed(seed)
        self.mean_daily_demand = mean_daily_demand
        self.std_daily_demand = std_daily_demand
        self.shipment_schedule = []
        self.inventory_history = []
        self.past_rops=[]
        self.backorders = 0
        self.fulfilled_demand = 0
        self.total_demand = 0
        self.out_of_stock = 0

    
    def simulate_order(self, order):
        print("generate order")
        
        for i in range(int(self.warehouse.eoq)):
            delivery_date = self.current_date + timedelta(days=i+1)
            self.shipment_schedule.append(Shipment(order_id=order.id, quantity=1, delivery_date=delivery_date))
        return order

    def simulate_deliveries(self):
        # 1. receive any delivereies
            for shipment in self.shipment_schedule:
                if shipment.delivery_date == self.current_date:
                    self.warehouse.receive_shipment(shipment=shipment, date=self.current_date)
                    self.shipment_schedule.remove(shipment)

    def simulate_demand(self):
        demand_today = max(0, int(np.random.normal(self.mean_daily_demand, self.std_daily_demand)))
            
        self.total_demand += demand_today   
        fulfilled_demand_today, backorders_today = self.warehouse.consume_inventory(self.current_date, demand_today)
        
        self.fulfilled_demand += fulfilled_demand_today
        self.backorders += backorders_today

        inventory_today, order = self.warehouse.monitor_inventory(self.current_date)

        if order:
            self.simulate_order(order)
              
        self.past_rops.append(self.warehouse.rop)
        self.inventory_history.append(inventory_today)
    
    def run(self):
        for day in range(self.days):
            self.current_date = self.start_date + timedelta(days=day)

            self.simulate_deliveries()
            self.simulate_demand()
            
            
            

    def evaluate(self):
        # --- Results ---
        service_level = self.fulfilled_demand / self.total_demand

        print("--- Simulation Results ---")
        print(f"Total demand: {self.total_demand}")
        print(f"Fulfilled demand: {self.fulfilled_demand}")
        print(f"Backorders: {self.backorders}")
        print(f"Orders placed: {self.warehouse.orders_placed}")
        print(f"Service level: {service_level:.2%}")

        # --- Visualization ---
        plt.figure(figsize=(12, 6))
        plt.plot(self.inventory_history, label='Inventory Level')
        plt.plot(self.past_rops, color='r', linestyle='--', label='Reorder Point')
        # plt.axhline(y=self.warehouse.rop, color='r', linestyle='--', label='Reorder Point')
        plt.title('Inventory Level Over Time')
        plt.xlabel('Day')
        plt.ylabel('Inventory')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
            


        