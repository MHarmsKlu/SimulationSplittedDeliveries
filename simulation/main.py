from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log,exp
import numpy as np

sku_config_1 = {
    'id' : 1,
    'rop' : 500,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'item_distribution_mean',
    'verbose': True
}

sku_config_2 = {
    'id' : 2,
    'rop' : 300,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 30,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'item_distribution_mean',
    'verbose': True
}

warehouse = Warehouse([sku_config_1,sku_config_2])

sim_config = {
    'start_date' : datetime.now(),
    'days' : 1000,
    'warehouse' : Warehouse(war_config),
    'seed': 11,  
    'mean_daily_demand' : 50,
    'std_daily_demand' : 1,
    'delivery_func' : [lambda x: 0.5*exp(-0.5*x),lambda x: 100],
    'delivery_split_centre' : 1,
    'delivery_split_std' : 1,
    'verbose': False
}

simulation = Simulation( config=sim_config)


simulation.run()
simulation.evaluate_globally(report=True)
simulation.visualize()