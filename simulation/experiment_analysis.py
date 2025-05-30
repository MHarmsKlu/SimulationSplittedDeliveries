import pandas
import numpy
import pm4py
import os, json
from collections import defaultdict
import statistics as st
import shutil
from warehouse import Warehouse, Warehouse_SKU
from simulation import Simulation
from datetime import date, time, datetime
from tqdm import tqdm

def analyse_trad_pm(path, type):
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

    dfg, placed, end = pm4py.discover_dfg(log)
    pm4py.save_vis_dfg(dfg, placed, end, f"{path}dfg.png")

    bpmn_graph = pm4py.discover_bpmn_inductive(log)
    pm4py.save_vis_bpmn(bpmn_graph, f"{path}bpmn.png",) 

    lead_times = []
    partial_lead_times = []
    num_splits = []
    num_partial_deliveries = []
    min_lead_times = []
    delivery_spread = []
    for case_id in log_df["CaseId"].unique():
        num_splits.append(log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Split Item")].shape[0])
        num_partial_deliveries.append(log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")].shape[0])
        placed = log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Place Order")]["Timestamp"].min()
        end = log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")]["Timestamp"].max()
        start = log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")]["Timestamp"].min()
        lead_times.append((end - placed).days)
        min_lead_times.append((start-placed).days)
        delivery_spread.append((end-start).days)
        all_partial_lead_times = []
        for _,end in log_df[(log_df["CaseId"]== case_id) & (log_df["Activity"]=="Deliver Package")].iterrows():
            all_partial_lead_times.append((end["Timestamp"]-placed).days)
        partial_lead_times.append(st.mean(all_partial_lead_times))
    mean_lead_time = st.mean(lead_times)
    mean_min_lead_time = st.mean(min_lead_times)
    mean_delivery_spread = st.mean(delivery_spread)
    mean_partial_lead_time = st.mean(partial_lead_times)
    mean_num_splits = st.mean(num_splits)
    mean_num_partial_deliveries = st.mean(num_partial_deliveries)

    return {f"{type}_num_events" :num_events, f"{type}_mean_lead_time" : mean_lead_time, f"{type}_mean_partial_lead_time": mean_partial_lead_time,
     f"{type}_mean_num_splits": mean_num_splits, f"{type}_mean_num_partial_deliveries": mean_num_partial_deliveries,
     f"{type}_mean_min_lead_time": mean_min_lead_time, f"{type}mean_delivery_spread": mean_delivery_spread}

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
    pm4py.save_vis_ocdfg(ocdfg, output, annotation='frequency',rankdir="tb")

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

    # leaves_sum = 0
    # for tree in split_trees.values():
    #     leaves_sum += len(tree.leaves)

    num_events = ocel.get_extended_table().shape[0]

    st_num_partial_deliveries= []
    st_num_splits = []
    st_lead_times = []
    st_min_lead_times = []
    st_partial_lead_times = []
    st_delivery_spread = []
    for tree in split_trees.values():
        st_num_splits.append(tree.splits)
        deliveries = []
        for leaf in tree.leaves:
            package = ocel.o2o[(ocel.o2o["ocel:oid_2"]==leaf)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].values[0]
            package_trace = pm4py.filter_ocel_objects(ocel, [package]).get_extended_table()
            deliveries.append(package_trace[package_trace['ocel:activity']== "Deliver Package"]["ocel:timestamp"].max())
        
        st_num_partial_deliveries.append(len(deliveries))
        start_trace = pm4py.filter_ocel_objects(ocel, [tree.root]).get_extended_table()
        start = start_trace[start_trace["ocel:activity"]=="Place Order"]["ocel:timestamp"].min()
        st_lead_times.append((max(deliveries)-start).days)
        st_min_lead_times.append((min(deliveries)-start).days)
        st_delivery_spread.append((max(deliveries)-min(deliveries)).days)
        all_partial_lead_times = []
        for end in deliveries:
            all_partial_lead_times.append((end-start).days)
        st_partial_lead_times.append(st.mean(all_partial_lead_times))
    st_mean_lead_time = st.mean(st_lead_times)
    
    st_mean_min_lead_time = st.mean(st_min_lead_times)
    st_mean_partial_lead_time = st.mean(st_partial_lead_times)
    st_mean_num_splits = st.mean(st_num_splits)
    st_mean_num_partial_deliveries = st.mean(st_num_partial_deliveries)
    st_mean_delivery_spread = st.mean(st_delivery_spread)


    order_num_partial_deliveries = []
    order_num_splits = []
    order_lead_times = []
    order_min_lead_times = []
    order_partial_lead_times = []
    order_delivery_spread = []

    for nested_root in nested_roots:
        order_split_trees = [split_trees[root] for root in nested_root]
        deliveries = pandas.DataFrame()
        start_trace = pm4py.filter_ocel_objects(ocel, nested_root).get_extended_table()
        start = start_trace[start_trace["ocel:activity"]=="Place Order"]["ocel:timestamp"].min()
        tree_num_splits = 0
        for tree in order_split_trees:
            tree_num_splits += tree.splits
            
            for leaf in tree.leaves:
                package = ocel.o2o[(ocel.o2o["ocel:oid_2"]==leaf)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].values[0]
                package_trace = pm4py.filter_ocel_objects(ocel, [package]).get_extended_table()
                deliveries = pandas.concat([deliveries,package_trace[package_trace['ocel:activity']== "Deliver Package"]])
        delivery_unique = deliveries.drop_duplicates(subset=["ocel:eid"])
        delivery_timestamps = delivery_unique["ocel:timestamp"]
        order_lead_times.append((delivery_timestamps.max()-start).days)
        order_min_lead_times.append((delivery_timestamps.min()-start).days)
        order_delivery_spread.append((delivery_timestamps.max()-delivery_timestamps.min()).days)
        order_num_partial_deliveries.append(len(delivery_timestamps))
        all_partial_lead_times = []
        for end in delivery_timestamps:
            all_partial_lead_times.append((end-start).days)
        order_partial_lead_times.append(st.mean(all_partial_lead_times))
        order_num_splits.append(tree_num_splits)
    order_mean_lead_time = st.mean(order_lead_times)
    order_mean_min_lead_time = st.mean(order_min_lead_times)
    order_mean_partial_lead_time = st.mean(order_partial_lead_times)
    order_mean_num_splits = st.mean(order_num_splits)
    order_mean_num_partial_deliveries = st.mean(order_num_partial_deliveries)
    order_mean_delivery_spread = st.mean(order_delivery_spread)

    flat_items = pm4py.ocel.ocel_flattening(ocel, object_type="Item")
    lead_times = []
    for item in flat_items["case:concept:name"].unique():
        trace = flat_items[flat_items["case:concept:name"]==item]
        if "Pack Items" in trace["concept:name"].unique():
            package = ocel.o2o[(ocel.o2o["ocel:oid_2"]==item)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].values[0]
            package_trace = pm4py.filter_ocel_objects(ocel, [package]).get_extended_table()
            lead_times.append((package_trace[package_trace['ocel:activity']== "Deliver Package"]["ocel:timestamp"].max()-trace["time:timestamp"].min()).days)

    case_lead_time = st.mean(lead_times)
    case_num_events = flat_items.shape[0]

    return {"ocpm_num_events" :num_events, "case_num_events": case_num_events, "case_lead_time": case_lead_time,
            "ocpm_st_mean_lead_time" : st_mean_lead_time, "ocpm_st_mean_partial_lead_time": st_mean_partial_lead_time, "ocpm_st_mean_num_splits" : st_mean_num_splits, "ocpm_st_mean_num_partial_deliveries" : st_mean_num_partial_deliveries,
            "ocpm_order_mean_lead_time" : order_mean_lead_time, "ocpm_order_mean_partial_lead_time": order_mean_partial_lead_time, "ocpm_order_mean_num_splits": order_mean_num_splits, "ocpm_order_mean_num_partial_deliveries": order_mean_num_partial_deliveries,
            "ocpm_st_mean_min_lead_time": st_mean_min_lead_time, "ocpm_st_mean_delivery_spread":st_mean_delivery_spread,"ocpm_order_mean_min_lead_time": order_mean_min_lead_time, "ocpm_order_mean_delivery_spread":order_mean_delivery_spread }
def analyse_ocpm_base(path,output):
    

    ocel = pm4py.read_ocel2_json("OCEL.json")
    #ocdfg = pm4py.discover_ocdfg(ocel)
    #pm4py.save_vis_ocdfg(ocdfg, output, annotation='frequency',rankdir="tb")

    items = ocel.objects[ocel.objects['ocel:type']=="Item"]["ocel:oid"].unique()
    lead_times= []
    min_lead_times = []
    delivery_spread = []
    avg_pckg_deliveries = []
    order_placed = pm4py.filter_ocel_event_attribute(ocel,'ocel:activity',['Place Order'])
    for order in ocel.objects[ocel.objects['ocel:type']=="Order"]["ocel:oid"].unique():
        deliveries = pandas.DataFrame()
        placed = pm4py.filter_ocel_objects(order_placed, [order]).get_extended_table()["ocel:timestamp"].min()
        placed_id = pm4py.filter_ocel_objects(order_placed, [order]).get_extended_table()["ocel:eid"].values[0]
        items = order_placed.get_extended_table()[order_placed.get_extended_table()["ocel:eid"]==placed_id]["ocel:type:Item"].values[0]
        for item in items:
        
            split_df = pm4py.filter_ocel_event_attribute(ocel,'ocel:activity',['Split Item']).get_extended_table()
            split_parents = ocel.relations[(ocel.relations["ocel:activity"]=="Split Item") & (ocel.relations["ocel:qualifier"]=="Split of available items for delivery")]
            try:
                split_id = split_parents[split_parents["ocel:oid"]==item]["ocel:eid"].to_numpy()[0]
                split = split_df[split_df["ocel:eid"]==split_id]["ocel:type:Item"].to_numpy()[0]
                split.remove(item)

                for split_item in split:
                    if not ocel.o2o[(ocel.o2o["ocel:oid_2"]==split_item)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].shape[0] == 0:
                        package = ocel.o2o[(ocel.o2o["ocel:oid_2"]==split_item)& (ocel.o2o["ocel:qualifier"]=="Package of item")]["ocel:oid"].values[0]
                        package_trace = pm4py.filter_ocel_objects(ocel, [package]).get_extended_table()
                        deliveries = pandas.concat([deliveries,package_trace[package_trace['ocel:activity']== "Deliver Package"]])
            except Exception:
                print("no splits")     
        if deliveries.shape[0] == 0:
            return {
                "ocpm_base_mean_lead_time" : numpy.nan, "ocpm_base_mean_partial_lead_time": numpy.nan, 
                "ocpm_base_mean_min_lead_time": numpy.nan, "ocpm_base_mean_delivery_spread":numpy.nan }
        else:
            delivery_unique = deliveries.drop_duplicates(subset=["ocel:eid"])
            lead_times.append((delivery_unique["ocel:timestamp"].max() -placed).days)
            min_lead_times.append((delivery_unique["ocel:timestamp"].min()-placed).days)
            delivery_spread.append((delivery_unique["ocel:timestamp"].max()-delivery_unique["ocel:timestamp"].min()).days)
            delivery_times = []
            for delivery in delivery_unique['ocel:timestamp']:
                delivery_times.append((delivery-placed).days)
            avg_pckg_deliveries.append(st.mean(delivery_times))
            mean_lead_time = st.mean(lead_times)
            mean_min_lead_time = st.mean(min_lead_times)
            mean_partial_lead_time = st.mean(avg_pckg_deliveries)
            mean_delivery_spread = st.mean(delivery_spread)
            return {
                "ocpm_base_mean_lead_time" : mean_lead_time, "ocpm_base_mean_partial_lead_time": mean_partial_lead_time, 
                "ocpm_base_mean_min_lead_time": mean_min_lead_time, "ocpm_base_mean_delivery_spread":mean_delivery_spread }

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
    'order_base_cost' : 50,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': False
}

sku_config_2 = {
    'id' : 2,
    'rop' : 300,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': False
}

sku_config_3 = {
    'id' : 3,
    'rop' : 300,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 50,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': False
}

sku_config_4 = {
    'id' : 4,
    'rop' : 300,
    'eoq' : 0,
    'z_score': 1.65,
    'order_base_cost' : 60,
    'holding_cost' : 1 , 
    'inventory' : 500,
    'kpi' : 'order_completion',
    'verbose': False
}
results = pandas.DataFrame()
for i in tqdm(range(1,11)):
    warehouse = Warehouse([sku_config_0,sku_config_1,sku_config_2, sku_config_3, sku_config_4, ])
    output = f"Output_{i}"
    sim_config = {
        'start_date' : datetime.now(),
        'days' : 1000,
        'warehouse' : warehouse,
        'seed': 11,  
        'mean_daily_demand' : 50,
        'std_daily_demand' : 1,
        'delivery_func' : [lambda x: 100,lambda x: 100, lambda x: 100, lambda x: 100, lambda x: 100],
        'delivery_split_centre' : i,
        'delivery_split_std' : i/10 if i > 1 else 0,
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

    # div_items_results = analyse_trad_pm(path=f"Output_{i}/div_items/", type="div_items")
    div_order_results = analyse_trad_pm(path=f"Output_{i}/div_order/", type="div_order")
    div_order_results["div_order_mean_min_lead_time"] = div_order_results["div_order_mean_lead_time"]
    div_order_results["div_order_mean_partial_lead_time"] = div_order_results["div_order_mean_min_lead_time"]
    div_order_results["div_order_mean_delivery_spread"] = 0
    # conv_results = analyse_trad_pm(path=f"Output_{i}/conv/", type="conv")
    ocpm_results = analyse_ocpm(path=f"Output_{i}/", output=f"Output_{i}/ocdfg.png")
    ocpm_results["case_min_lead_time"] = ocpm_results["case_lead_time"]
    ocpm_results["case_partial_lead_time"] = ocpm_results["case_lead_time"]
    ocpm_results["case_delivery_spread"] = 0
    ocpm_base_results = analyse_ocpm_base(path=f"Output_{i}/", output=f"Output_{i}/ocdfg.png")
    # iteration_results_dict = {"mean_splits": i, **div_items_results, **div_order_results,**conv_results,**ocpm_results}
    iteration_results_dict = {"mean_splits": i,**div_order_results, **ocpm_results, **ocpm_base_results }
    iteration_results_df = pandas.DataFrame.from_dict(iteration_results_dict, orient='index').T
    results = pandas.concat([results,iteration_results_df])

results.reset_index(drop=True).to_excel("results.xlsx")
    # simulation.evaluate_globally(report=True)
    # for sku in warehouse.SKUs.keys():
    #     simulation.evaluate_skus(sku, report=True)
    # simulation.visualize()

# - [x] lead time check
# - [x] average partial shipment lead time
# - [x] first delivery
# - [x] delivery spread 
# - [] partial fulfilment