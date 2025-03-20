import os
import time

import numpy as np

from mnms.simulation import Supervisor
from mnms.demand import CSVDemandManager
from mnms.flow.MFD import Reservoir, MFDFlowMotor
from mnms.log import attach_log_file, LOGLEVEL, set_mnms_logger_level
from mnms.time import Time, Dt
from mnms.io.graph import load_graph, load_odlayer, save_graph, save_odlayer, save_transit_link_odlayer, \
    load_transit_links
from mnms.travel_decision.custom_decision_model import BCDecisionModel
from mnms.travel_decision.logit import LogitDecisionModel
from mnms.tools.observer import CSVUserObserver, CSVVehicleObserver
from mnms.generation.layers import generate_bbox_origin_destination_layer
from mnms.mobility_service.personal_vehicle import PersonalMobilityService
from mnms.mobility_service.public_transport import PublicTransportMobilityService
import json
import shutil
import pandas as pd

def ensure_outputs_dir():
    """Checks if the 'OUTPUTS' directory exists. If it does, deletes it and creates a new one. Otherwise, creates the directory."""

    outputs_dir = "OUTPUTS"  # Define the directory name

    if os.path.exists(outputs_dir):
        try:
            shutil.rmtree(outputs_dir)  # Delete the existing directory and its contents
            print(f"Deleted existing '{outputs_dir}' directory.")
        except OSError as e:
            print(f"Error deleting '{outputs_dir}': {e}")
            return  # Exit the function if deletion fails.

    try:
        os.makedirs(outputs_dir)  # Create the new directory
        print(f"Created new '{outputs_dir}' directory.")
    except OSError as e:
        print(f"Error creating '{outputs_dir}': {e}")


def rename_outputs_dir(new_dir_name):
    """Renames the 'OUTPUTS' directory to 'BASELINE' or 'TEST' based on the 'baseline' flag.

    Args:
        baseline (bool): If True, renames to 'BASELINE'; otherwise, renames to 'TEST'.
    """

    outputs_dir = "OUTPUTS"

    if os.path.exists(outputs_dir):
        try:
            os.rename(outputs_dir, new_dir_name)
            print(f"Renamed '{outputs_dir}' to '{new_dir_name}'.")
        except OSError as e:
            print(f"Error renaming '{outputs_dir}' to '{new_dir_name}': {e}")
    else:
        print(f"'{outputs_dir}' directory does not exist. Creating '{new_dir_name}'")
        try:
            os.makedirs(new_dir_name)
        except OSError as e:
            print(f"Error creating '{new_dir_name}': {e}")

indir = "INPUTS"
outdir = "OUTPUTS"

ensure_outputs_dir()

# set_all_mnms_logger_level(LOGLEVEL.WARNING)
set_mnms_logger_level(LOGLEVEL.INFO, ["mnms.simulation"])

#get_logger("mnms.graph.shortest_path").setLevel(LOGLEVEL.WARNING)
attach_log_file(outdir + '/simulation.log')


# 'DESTINATION_R_82604106' 'ORIGIN_E_83202447'

def calculate_V_MFD(acc):
    #V = 10.3*(1-N/57000) # data from fit prop
    V = 0  # data from fit dsty
    N = acc["CAR"]
    if N < 18000:
        V = 11.5 - N * 6 / 18000
    elif N < 55000:
        V = 11.5 - 6 - (N - 18000) * 4.5 / (55000 - 18000)
    elif N < 80000:
        V = 11.5 - 6 - 4.5 - (N - 55000) * 1 / (80000 - 55000)
    #V = 11.5*(1-N/60000)
    V = max(V, 0.001)  # min speed to avoid gridlock
    V_TRAM_BUS = 0.7 * V
    return {"CAR": V, "METRO": 17, "BUS": V_TRAM_BUS, "TRAM": V_TRAM_BUS}


def load_capacity_info(capacity_file):
    print("Loading capacity info from {}".format(capacity_file))
    capacity_info = {}
    with open(capacity_file, 'r') as f:
        pt_network = json.load(f)
        for i in range(len(pt_network['LAYERS'])):
            layer = pt_network['LAYERS'][i]
            layer_id = layer['ID']
            if 'METRO' in layer_id or 'BUS' in layer_id or 'TRAM' in layer_id:
                for k in range(len(layer['LINES'])):
                    veh = layer['LINES'][k]['ID']
                    capacity_info[veh] = layer['LINES'][k]['CAPACITY']
    return capacity_info


def force_public_transport(demand_file):
    print('Forcing public transport from {}'.format(demand_file))
    demand_data = pd.read_csv(demand_file, sep=';')
    print('N queries:', len(demand_data), 'N users:', len(np.unique(demand_data['ID'])))
    if 'MOBILITY SERVICES' not in demand_data.columns:
        demand_data['MOBILITY SERVICES'] = 'METRO TRAM BUS'
        demand_data.to_csv(demand_file, sep=';', index=False)


if __name__ == '__main__':
    NX = 100
    NY = 100
    #DIST_CONNECTION = 1e2

    mmgraph = load_graph(indir + "/lyon_network_gtfs_mod.json")
    start_time = time.time()
    odlayer = generate_bbox_origin_destination_layer(mmgraph.roads, NX, NY)
    mmgraph.odlayer = odlayer
    end_time = time.time()
    print('OD LAYER CREATION', end_time - start_time, 's')

    ##
    # start_time = time.time()
    mmgraph.add_origin_destination_layer(odlayer)
    # mmgraph.connect_origindestination_layers(500, 1000)
    # end_time = time.time()
    # print('MMGRAPH LAYER CREATION', end_time - start_time, 's')

    if not os.path.exists(indir + f"/transit_link_{NX}_{NY}_{500}_grid.json"):
        mmgraph.connect_origindestination_layers(500,1000)
        save_transit_link_odlayer(mmgraph, indir + f"/transit_link_{NX}_{NY}_{500}_grid.json")
    else:
        start_time = time.time()
        load_transit_links(mmgraph, indir + f"/transit_link_{NX}_{NY}_{500}_grid.json")
        end_time = time.time()
        print('MMGRAPH LAYER UPLOADING', end_time - start_time, 's')

    personal_car = PersonalMobilityService()
    personal_car.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["CAR"].add_mobility_service(personal_car)

    capacity_info = load_capacity_info(indir + "/lyon_network_gtfs_mod.json")

    bus_service = PublicTransportMobilityService("BUS", capacity_info=capacity_info)
    bus_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["BUSLayer"].add_mobility_service(bus_service)

    tram_service = PublicTransportMobilityService("TRAM", capacity_info=capacity_info)
    tram_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["TRAMLayer"].add_mobility_service(tram_service)

    metro_service = PublicTransportMobilityService("METRO", capacity_info=capacity_info)
    metro_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["METROLayer"].add_mobility_service(metro_service)

    demand_file_name = indir + "/demand_custom_allday.csv"
    force_public_transport(demand_file_name)
    demand = CSVDemandManager(demand_file_name)
    demand.add_user_observer(CSVUserObserver(outdir + "/user.csv"), user_ids="all")

    # mmgraph.connect_intra_layer("BUSLayer", 500)
    # mmgraph.connect_intra_layer("TRAMLayer", 500)
    # mmgraph.connect_intra_layer("METROLayer", 500)
    # mmgraph.connect_inter_layers(["BUSLayer", "TRAMLayer", "METROLayer"], 500)

    start_time = time.time()
    load_transit_links(mmgraph, indir + f'/mmgraph_{NX}_{NX}_{500}.json')
    end_time = time.time()
    print(f'LOADING MMGRAPH INTER-INTRA LAYER', end_time - start_time, 's')

    flow_motor = MFDFlowMotor(outfile=outdir + "/flow.csv")
    flow_motor.add_reservoir(Reservoir(mmgraph.roads.zones["RES"], ["CAR"], calculate_V_MFD))

    #travel_decision = LogitDecisionModel(mmgraph, outfile=outdir + "/path.csv")
    sim_type = 'QoEdriven'
    print(f'SIMULATION TYPE:', sim_type)
    travel_decision = BCDecisionModel(mmgraph, outfile=outdir + "/path.csv", 
                                                     sim_type=sim_type, top_k=5, n_shortest_path=10, 
                                                     max_diff_cost = 0.90,
                                                     max_dist_in_common = 0.98,
                                                     cost_multiplier_to_find_k_paths = 1.1,)

    supervisor = Supervisor(graph=mmgraph,
                            flow_motor=flow_motor,
                            demand=demand,
                            decision_model=travel_decision,
                            outfile=outdir + "/travel_time_link.csv")

    start = time.time()
    supervisor.run(Time('07:00:00'), Time('09:00:00'), Dt(seconds=30), 1)
    end = time.time()
    print(f'SIMULATION COMPLETED IN {end-start} s')
    
    rename_outputs_dir(sim_type)
