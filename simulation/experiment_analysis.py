import pandas
import pm4py
import os, json
from collections import defaultdict
import statistics as st
import shutil
from warehouse import Warehouse, Warehouse_SKU
from simulation import Simulation
from datetime import date, time, datetime
from tqdm import tqdm

def analyse_trad_pm(path, output):
    csv_files = [pos_csv for pos_csv in os.listdir(path) if pos_csv.endswith('.csv')]

    log_df = pandas.DataFrame()
    for index, csv in enumerate(csv_files):
        with open(os.path.join(path, csv)) as csv_file:
            case_dataframe = pandas.read_csv(csv_file)
            log_df = pandas.concat([log_df,case_dataframe])

    log_df = pm4py.format_dataframe(log_df, case_id='CaseId', activity_key='Activity', timestamp_key='Timestamp')
    log = pm4py.convert_to_event_log(log_df)

    cases = log_df['CaseId'].nunique()
    num_events = log_df.shape[0]

    dfg, start, end = pm4py.discover_dfg(log)
    
    pm4py.save_vis_dfg(dfg, start, end, output)

    lead_times = []
    partial_lead_times = []
    for case_id in log_df["CaseId"].unique():
        start = log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Place Order")]["Timestamp"].min()
        end = log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")]["Timestamp"].max()
        lead_times.append((end - start).days)

        for _,end in log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")].iterrows():
            partial_lead_times.append((end["Timestamp"]-start).days)
    
    mean_lead_time = st.mean(lead_times)
    mean_partial_lead_time = st.mean(partial_lead_times)

    return num_events, mean_lead_time, mean_partial_lead_time

class Split_tree:
    def __init__(self,root):
        self.root = root
        self.nodes = [root]
        self.leaves = []
        self.splits = 0

def analyse_ocpm(path,output):
    complete_ocel_json = {}
    complete_ocel_json["objects"] = []
    complete_ocel_json["events"] =[]
    o_count = 0
   
    json_files = [pos_json for pos_json in os.listdir(path) if pos_json.endswith('.json')]
    with open(os.path.join(path,json_files[0])) as init_js:
        json_text = json.load(init_js)
        complete_ocel_json["objectTypes"]= json_text["objectTypes"]
        complete_ocel_json["eventTypes"]= json_text["eventTypes"]

    for index, js in enumerate(json_files):
        with open(os.path.join(path, js)) as json_file:
            json_ocel = json.load(json_file)
            o_count += len(json_ocel["objects"])
            complete_ocel_json["objects"] +=(json_ocel["objects"])
            complete_ocel_json["events"]+=(json_ocel["events"])

    # Serializing json
    json_object = json.dumps(complete_ocel_json)

    # Writing to sample.json
    with open("OCEL.json", "w") as outfile:
        outfile.write(json_object)

    ocel = pm4py.read_ocel2_json("OCEL.json")
    ocdfg = pm4py.discover_ocdfg(ocel)
    pm4py.save_vis_ocdfg(ocdfg, output, annotation='frequency')

    items = ocel.objects[ocel.objects['ocel:type']=="Item"]["ocel:oid"].unique()
    order_placed = pm4py.filter_ocel_event_attribute(ocel,'ocel:activity',['Place Order'])

    nested_roots = order_placed.get_extended_table()["ocel:type:Item"].tolist()
    roots = []
    for nested_root in nested_roots:
        for root in nested_root:
            roots.append(root)

    split_df = pm4py.filter_ocel_event_attribute(ocel,'ocel:activity',['Split Item']).get_extended_table()
    split_parents = ocel.relations[(ocel.relations["ocel:activity"]=="Split Item") & (ocel.relations["ocel:qualifier"]=="Split of available items for delivery")]
    split_trees={}

    for root in roots:
        split_trees[root]=(Split_tree(root))

    
    for root in roots:
        queue = [root]
        while queue:
            current = queue.pop(0)
            if current in split_parents["ocel:oid"].copy().to_numpy():
                split_id = split_parents[split_parents["ocel:oid"]==current]["ocel:eid"].to_numpy()[0]
                split = split_df[split_df["ocel:eid"]==split_id]["ocel:type:Item"].to_numpy()[0]
                split.remove(current)
                split_trees[root].nodes += split
                queue += split
                split_trees[root].splits += 1
            else:
                split_trees[root].leaves.append(current)

    leaves_sum = 0
    for tree in split_trees.values():
        leaves_sum += len(tree.leaves)

    num_events = ocel.get_extended_table().shape[0]

    lead_times = []
    partial_lead_times = []
    for tree in split_trees.values():
        deliveries = []
        for leave in tree.leaves:
            package = ocel.o2o[(ocel.o2o["ocel:oid_2"]==leave)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].values[0]
            package_trace = pm4py.filter_ocel_objects(ocel, [package]).get_extended_table()
            deliveries.append(package_trace[package_trace['ocel:activity']== "Deliver Package"]["ocel:timestamp"].max())
        start_trace = pm4py.filter_ocel_objects(ocel, [tree.root]).get_extended_table()
        start = start_trace[start_trace["ocel:activity"]=="Place Order"]["ocel:timestamp"].min()
        lead_times.append((max(deliveries)-start).days)
        for end in deliveries:
            partial_lead_times.append((end-start).days)

    mean_lead_time = st.mean(lead_times)
    mean_partial_lead_time = st.mean(partial_lead_times)

    return num_events, mean_lead_time, mean_partial_lead_time

sku_config_0 = {
    'id' : 0,
    'rop' : 500,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': False
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
    'verbose': False
}
results = {}
for i in tqdm(range(0,11)):
    warehouse = Warehouse([sku_config_0,sku_config_1])
    output = f"Output_{i}"
    sim_config = {
        'start_date' : datetime.now(),
        'days' : 1000,
        'warehouse' : warehouse,
        'seed': 11,  
        'mean_daily_demand' : 50,
        'std_daily_demand' : 1,
        'delivery_func' : [lambda x: 100,lambda x: 100],
        'delivery_split_centre' : i,
        'delivery_split_std' : i/10 if i > 0 else 0,
        'verbose': False,
        'output' : output
    }
    
    try:
        shutil.rmtree(output)
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    os.makedirs(output)
    simulation = Simulation( config=sim_config)

    simulation.run()

    div_results = analyse_trad_pm(path=f"Output_{i}/div/", output=f"Output_{i}/div/dfg.png")
    conv_results = analyse_trad_pm(path=f"Output_{i}/conv/", output=f"Output_{i}/conv/dfg.png")
    ocpm_results = analyse_ocpm(path=f"Output_{i}/", output=f"Output_{i}/ocdfg.png")
    results[i] = [div_results,conv_results,ocpm_results]
    # simulation.evaluate_globally(report=True)
    # for sku in warehouse.SKUs.keys():
    #     simulation.evaluate_skus(sku, report=True)
    # simulation.visualize()

