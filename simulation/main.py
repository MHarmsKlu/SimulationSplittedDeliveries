from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log,exp
import numpy as np

war_config = {
    'rop' : 500,
    'eoq' : 0,
    'service_level': 0.95,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': True
}


sim_config = {
    'start_date' : datetime.now(),
    'days' : 200,
    'warehouse' : Warehouse(war_config),
    'seed': 12,  
    'mean_daily_demand' : 50,
    'std_daily_demand' : 1,
    'delivery_func' : lambda x: 0.1*exp(-0.10*x),
    'delivery_split_centre' : 10,
    'delivery_split_std' : 1,
    'verbose': True
}

simulation = Simulation( config=sim_config)


simulation.run()
simulation.evaluate(report=True)
simulation.visualize()