from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log,exp
import numpy as np
import os
import sys
import shutil


output = "Output"

# Try to remove the tree; if it fails, throw an error using try...except.
try:
    shutil.rmtree(output)
except OSError as e:
    print("Error: %s - %s." % (e.filename, e.strerror))

sku_config_0 = {
    'id' : 0,
    'rop' : 500,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': True
}

sku_config_1 = {
    'id' : 1,
    'rop' : 300,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 30,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': True
}

warehouse = Warehouse([sku_config_0,sku_config_1])

sim_config = {
    'start_date' : datetime.now(),
    'days' : 1000,
    'warehouse' : warehouse,
    'seed': 11,  
    'mean_daily_demand' : 50,
    'std_daily_demand' : 1,
    'delivery_func' : [lambda x: 0.5*exp(-0.5*x),lambda x: 100],
    'delivery_split_centre' : 5,
    'delivery_split_std' : 1,
    'verbose': False,
    'output' : 'Output'
}

simulation = Simulation( config=sim_config)


simulation.run()
simulation.evaluate_globally(report=True)
for sku in warehouse.SKUs.keys():
    simulation.evaluate_skus(sku, report=True)
simulation.visualize()