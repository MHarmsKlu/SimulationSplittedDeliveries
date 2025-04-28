from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin


warehouse = Warehouse(
     init_rop = 1000,
     init_eoq = 0,
     order_base_cost = 100,
     order_piece_cost = 50,
     holding_cost = 100 , 
     init_level = 1500,
     kpi = 'order_completion'
)

simulation = Simulation(
    start_date = datetime.now(),
    days = 10000,
    warehouse = warehouse,
    seed= 11,  
    mean_daily_demand = 5,
    std_daily_demand = 1,
    delivery_func = lambda x: 100 
)

simulation.run()
simulation.evaluate()