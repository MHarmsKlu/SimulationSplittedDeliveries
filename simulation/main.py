from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime


warehouse = Warehouse(
     init_rop = 100,
     init_eoq = 200,
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
    mean_daily_demand = 50,
    std_daily_demand = 10
)

simulation.run()
simulation.evaluate()