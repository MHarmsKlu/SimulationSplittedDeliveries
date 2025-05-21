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
        keys= ['start_date', 'days', 'warehouse', 'seed', 'mean_daily_demand','std_daily_demand','delivery_func', 'delivery_split_centre', 'delivery_split_std', 'output','verbose']
        for key in keys:
            setattr(self, key, config.get(key))
        
        self.current_date = self.start_date
        self.shipment_schedule = []
        self.global_backorders = 0
        self.global_fulfilled_demand = 0
        self.total_demand = 0
        self.global_out_of_stock = 0
        self.global_total_holding_costs = 0
        self.global_inventory_history_on_hand = []
        self.global_inventory_history_in_transit=[]
        self.global_inventory_history_total=[]

        self.sku_data = {}
        for sku in self.warehouse.SKUs.keys():
            self.sku_data[sku] = {
                'inventory_history_on_hand' : [],
                'inventory_history_in_transit' : [],
                'inventory_history_total' : [],
                'past_rops':[],
                'past_eoqs':[],
                'past_safety_stock':[],
                'backorders' : 0,
                'fulfilled_demand' : 0,
                'total_demand' : 0,
                'out_of_stock' : 0,
                'total_holding_costs' : 0,
            }
        self.sku_results={}
    
    def simulate_order(self, order):
        if self.verbose:
            print(f"generate order {order.id} with quantity {order.quantity}")
        ocel_config = {}
        for sku_id, sku in order.SKUs.items():
            delivery_days = max(1, int(np.random.normal(self.delivery_split_centre, self.delivery_split_std)))
            ocel_config[sku_id] = {'amount': sku.quantity, 'del_days': delivery_days, 'func':  self.delivery_func[sku_id]}
        generate_ocel_event_log(start_date=self.current_date, items=ocel_config, iteration=order.id, output=self.output)
        
        date_str = adjust_to_weekday(self.current_date).strftime("%Y-%m-%d")
        ocel = pm.read_ocel2_json(f"{self.output}/OrderProcess_{date_str}.json")
        filtered_ocel = pm.filter_ocel_event_attribute(ocel,'ocel:activity',['Deliver Package'])

        relations_with_timestamps = filtered_ocel.events.merge(filtered_ocel.relations, on="ocel:eid", ).drop(columns=['company',
            'payment_method', 'checker', 'spliter', 'picker', 'packer', 'storer','loader', 'logistics_company', 'ocel:activity_y',
            'ocel:timestamp_y', 'ocel:type', 'ocel:qualifier'],
            errors="ignore")
        shipments_with_time_and_qty = relations_with_timestamps.merge(filtered_ocel.objects, on="ocel:oid")

        for id,shipment in shipments_with_time_and_qty.iterrows():
            # TODO: refactor to multiple SKUs once maxis part is done
            goods = {}
            for item in ocel.o2o[ocel.o2o['ocel:oid']==shipment['ocel:oid']]['ocel:oid_2'].unique():
                item_obj = ocel.objects[ocel.objects['ocel:oid']==item]
                goods[int(item_obj['material_id'].values[0])] = item_obj["amount"].values[0]

            self.shipment_schedule.append(Shipment(ship_id=id, order_id=order.id, goods=goods, delivery_date=shipment["ocel:timestamp_x"].to_pydatetime()))
    
    def simulate_deliveries(self):
        # 1. receive any delivereies
            for shipment in self.shipment_schedule[:]:
                if shipment.delivery_date.date() == self.current_date.date():
                    self.warehouse.receive_shipment(shipment=shipment)

                    self.shipment_schedule.remove(shipment)

    def simulate_demand(self):
        demands = {}
        for sku in self.warehouse.SKUs.keys():
            demands[sku] = max(0, int(np.random.normal(self.mean_daily_demand, self.std_daily_demand))) 
        demand_today = sum(demands.values())
        fulfilled_demand_today, backorders_today = self.warehouse.consume_inventory(self.current_date, demands)
        
        order = self.warehouse.monitor_inventory(self.current_date)
        if order:
            self.simulate_order(order)
        return demand_today, fulfilled_demand_today, backorders_today       
    
    def collect_global_data(self, demand_today, fulfilled_demand_today, backorders_today):
        self.total_demand += demand_today
        self.global_fulfilled_demand += fulfilled_demand_today
        self.global_backorders += backorders_today  
        self.global_total_holding_costs += self.warehouse.current_holding_cost
        # self.past_rops.append(self.warehouse.rop)
        # self.past_eoqs.append(self.warehouse.eoq)

        self.global_inventory_history_on_hand.append(self.warehouse.inventory)
        self.global_inventory_history_in_transit.append(self.warehouse.inventory_in_transit)
        self.global_inventory_history_total.append(self.warehouse.inventory + self.warehouse.inventory_in_transit)

        if self.warehouse.inventory == 0:
            self.global_out_of_stock += 1
    
    def collect_sku_data(self, sku):
        self.sku_data[sku]['inventory_history_on_hand'].append(self.warehouse.SKUs[sku].inventory)
        self.sku_data[sku]['inventory_history_in_transit'].append(self.warehouse.SKUs[sku].inventory_in_transit)
        self.sku_data[sku]['inventory_history_total'].append(self.warehouse.SKUs[sku].inventory + self.warehouse.SKUs[sku].inventory_in_transit)
        self.sku_data[sku]['past_rops'].append(self.warehouse.SKUs[sku].rop)
        self.sku_data[sku]['past_eoqs'].append(self.warehouse.SKUs[sku].eoq)
        self.sku_data[sku]['past_safety_stock'].append(self.warehouse.SKUs[sku].safety_stock)
            
    def run(self):
        np.random.seed(self.seed)
        if self.verbose:
            print(f'start sim at {self.current_date}')
        for day in range(self.days):
            self.current_date = self.start_date + timedelta(days=day)

            self.simulate_deliveries()
            demand_today, fulfilled_demand_today, backorders_today = self.simulate_demand()
            
            self.collect_global_data(demand_today, fulfilled_demand_today, backorders_today)
            for sku in self.warehouse.SKUs.keys():
                self.collect_sku_data(sku)

            

    def evaluate_globally(self,report=False):
        # --- Results ---
        self.results = {
            'service_level' : self.global_fulfilled_demand / self.total_demand,
            'total_demand' : self.total_demand,
            'fulfilled_demand' : self.global_fulfilled_demand,
            'backorders' : self.global_backorders,
            'stock_outs' : self.global_out_of_stock,
            'orders_placed' : self.warehouse.orders_placed,
            'total_holding_costs' : self.global_total_holding_costs,
            'total_inventory_on_hand' : sum(self.global_inventory_history_on_hand),
            # 'mean_lead_time' : st.mean(self.warehouse.order_performances),
            # 'mean_order_size' : st.mean(self.warehouse.order_sizes)
        }
        if report == True:
            for key, value in self.results.items():
                print(f"{key}: {value}")

        return self.results
    
    def evaluate_skus(self, sku, report=False):
        self.sku_results[sku] = {
            'service_level' : self.warehouse.SKUs[sku].fulfilled_demand / self.warehouse.SKUs[sku].total_demand,
            'total_demand' : self.warehouse.SKUs[sku].total_demand,
            'fulfilled_demand' : self.warehouse.SKUs[sku].fulfilled_demand,
            'backorders' : self.warehouse.SKUs[sku].backorders,
            'stock_outs' : self.warehouse.SKUs[sku].out_of_stock,
            'total_holding_costs' : self.warehouse.SKUs[sku].total_holding_costs,
            'total_inventory_on_hand' : sum(self.sku_data[sku]['inventory_history_on_hand']),
            # 'mean_lead_time' : st.mean(self.warehouse.order_performances),
            # 'mean_order_size' : st.mean(self.warehouse.order_sizes)
        }
        if report == True:
            for key, value in self.sku_results[sku].items():
                print(f"{key}: {value}")

        return self.results
    def visualize(self):
        # --- Visualization ---
        plt.figure(figsize=(12, 6))
        plt.plot(self.global_inventory_history_on_hand, label='Inventory On hand')
        #plt.plot(self.global_inventory_history_in_transit, label='Inventory in transit')
        plt.plot(self.global_inventory_history_total, label='Total Inventory')
        # plt.plot(self.past_rops, color='r', linestyle='--', label='Reorder Point')
        # plt.plot(self.past_eoqs, color='y', linestyle='--', label='EOQ')
        # plt.plot(self.past_safety_stock, color='g', linestyle='--', label='safety stock')
        plt.title('Inventory Level Over Time')
        plt.xlabel('Day')
        plt.ylabel('Inventory')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
            

        