from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log
import numpy as np

war_config = {
    'rop' : 500,
    'eoq' : 0,
    'service_level': 0.95,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'item_completion',
    'verbose': False
}


sim_config = {
    'start_date' : datetime.now(),
    'days' : 1750,
    'warehouse' : Warehouse(war_config),
    'seed': 11,  
    'mean_daily_demand' : 50,
    'std_daily_demand' : 1,
    'delivery_func' : lambda x: 100,
    'delivery_split_centre' : 5,
    'delivery_split_std' : 1,
    'verbose': False
}

simulation = Simulation( config=sim_config)


simulation.run()
simulation.evaluate(report=True)
simulation.visualize()