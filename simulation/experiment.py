from math import log,sin
from simulation import Simulation
from warehouse import Warehouse
from datetime import date, time, datetime
from math import sin,log
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import shutil
import os

def initialize_sim(kpi, sku_config, sim_config, test_param, test_value):
    if test_param in sku_config.keys():
        sku_config[test_param]= test_value
    elif test_param in sim_config.keys():
        sim_config[test_param] = test_value
    else: 
        print(f"invalid test_param {test_param}")
    
    sku_config['kpi'] = kpi
    sim_config["warehouse"] = Warehouse([sku_config])
    return Simulation( config=sim_config)

def experiment(KPIs,sku_config, sim_config,test_param,init_value, step_size, max_value, target_params):
    try:
        shutil.rmtree(sim_config['output'])
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    os.makedirs(sim_config['output'])

    results = {}
    for target_param in target_params:
        results[target_param] = {}
    
    for kpi in tqdm(KPIs):
        for target_param in target_params:
            results[target_param][kpi] = []
        for i in tqdm(range(init_value,max_value,step_size)):
            sim = initialize_sim(kpi,sku_config,sim_config,test_param,i)

            sim.run()
            sim_results = sim.evaluate_globally()
            for target_param in target_params:
                results[target_param][kpi].append(sim_results[target_param]) 
    
    for target_param in target_params:
        plt.figure(figsize=(12, 6))
        for kpi in KPIs:
            plt.plot(results[target_param][kpi], label=kpi)
        plt.title(target_param)
        plt.xlabel(test_param)
        plt.ylabel(target_param)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    
KPIs = [
    "order_completion",
    "item_completion",
    #"item_distribution_mean"
]

delivery_functions = [
    lambda x: 1,
    lambda x: x**2,
    lambda x: -log(x)
]
sku_config = {
    'id' : 0,
    'rop' : 500,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'verbose': False
}

sim_config =  {
    'start_date' : datetime.now(),
    'days' : 1750,
    'seed': 1,  
    'mean_daily_demand' : 50,
    'std_daily_demand' : 1,
    'delivery_func' : [lambda x: 100],
    'delivery_split_centre' : 0,
    'delivery_split_std' : 1,
    'output': "experiment"}

target_params = ["service_level", "total_inventory_on_hand"]

experiment(KPIs,sku_config,sim_config, "delivery_split_centre", 1,1, 10, target_params  )
