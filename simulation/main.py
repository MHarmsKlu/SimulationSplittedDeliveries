from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime


warehouse = Warehouse(
     init_rop = 50,
     init_eoq = 100,
     order_base_cost = 50,
     order_piece_cost = 5,
     holding_cost = 10 , 
     init_level = 200,
     kpi = 'order_completion'
)

simulation = Simulation(
    start_date = datetime.now(),
    days = 1000,
    warehouse = warehouse,
    seed= 42,  
    mean_daily_demand = 5,
    std_daily_demand = 1,
    delivery_func = lambda x: x ** 2
)

simulation.run()
simulation.evaluate()