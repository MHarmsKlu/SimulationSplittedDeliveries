from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log


warehouse = Warehouse(
     init_rop = 500,
     init_eoq = 0,
     safety_stock= 500,
     order_base_cost = 100,
     holding_cost = 10 , 
     init_level = 500,
     kpi = 'order_completion'
)

simulation = Simulation(
    start_date = datetime.now(),
    days = 1750,
    warehouse = warehouse,
    seed= 11,  
    mean_daily_demand = 10,
    std_daily_demand = 1,
    delivery_func = lambda x: 100,
    delivery_split_centre = 5,
    delivery_split_std = 1
)

simulation.run()
simulation.evaluate()