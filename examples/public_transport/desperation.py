import os

from mnms.simulation import Supervisor
from mnms.demand import CSVDemandManager
from mnms.flow.MFD import Reservoir, MFDFlowMotor
from mnms.log import attach_log_file, LOGLEVEL, get_logger, set_all_mnms_logger_level, set_mnms_logger_level
from mnms.time import Time, Dt
from mnms.io.graph import load_graph, load_odlayer
from mnms.travel_decision.logit import LogitDecisionModel
from mnms.tools.observer import CSVUserObserver, CSVVehicleObserver
from mnms.generation.layers import generate_bbox_origin_destination_layer
from mnms.mobility_service.personal_vehicle import PersonalMobilityService
from mnms.mobility_service.public_transport import PublicTransportMobilityService
from mnms.io.graph import save_transit_link_odlayer, load_transit_links
import json

import pandas as pd

indir = "INPUTS"
outdir = "OUTPUTS"

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
                    capacity_info[veh] = 10

    return capacity_info


def force_public_transport(demand_file):
    print('Forcing public transport from {}'.format(demand_file))
    demand_data = pd.read_csv(demand_file, sep=';')
    if 'PATH' in demand_data.columns:
        demand_data = demand_data.drop(columns=['PATH'])
    if 'CHOSEN SERVICES' in demand_data.columns:
        demand_data = demand_data.drop(columns=['CHOSEN SERVICES'])
    demand_data['ORIGIN'] = '846073.08 6517678.81'
    demand_data['DESTINATION'] = '842387.30 6519213.73'
    for i, row in demand_data.iterrows():
        if int(i) % 2 != 0:
            path = 'ORIGIN_55 TRAM_T2_DIR2_TRAM_T2_DIR2_BachutMairiedu8eme TRAM_T2_DIR2_TRAM_T2_DIR2_Villon TRAM_T2_DIR2_TRAM_T2_DIR2_JetdEauMFrance TRAM_T2_DIR2_TRAM_T2_DIR2_RoutedeVienne TRAM_T2_DIR2_TRAM_T2_DIR2_GaribaldiBerthelot TRAM_T2_DIR2_TRAM_T2_DIR2_JeanMace TRAM_T2_DIR2_TRAM_T2_DIR2_CentreBerthelot TRAM_T2_DIR2_TRAM_T2_DIR2_Perrache TRAM_T2_DIR2_TRAM_T2_DIR2_PlacedesArchives TRAM_T2_DIR2_TRAM_T2_DIR2_SainteBlandine TRAM_T2_DIR2_TRAM_T2_DIR2_HotelRegionMontrochet DESTINATION_54'
            demand_data.loc[i, 'PATH'] = path
            demand_data.loc[i, 'CHOSEN SERVICES'] = 'TRANSIT:WALK ' + 'TRAMLayer:TRAM ' * path.count('TRAM') + 'TRANSIT:WALK'
        else:
            path = 'ORIGIN_55 TRAM_T2_DIR2_TRAM_T2_DIR2_JetdEauMFrance TRAM_T2_DIR2_TRAM_T2_DIR2_RoutedeVienne TRAM_T2_DIR2_TRAM_T2_DIR2_GaribaldiBerthelot TRAM_T2_DIR2_TRAM_T2_DIR2_JeanMace TRAM_T2_DIR2_TRAM_T2_DIR2_CentreBerthelot TRAM_T2_DIR2_TRAM_T2_DIR2_Perrache TRAM_T2_DIR2_TRAM_T2_DIR2_PlacedesArchives TRAM_T2_DIR2_TRAM_T2_DIR2_SainteBlandine TRAM_T2_DIR2_TRAM_T2_DIR2_HotelRegionMontrochet DESTINATION_54'
            demand_data.loc[i, 'PATH'] = path
            demand_data.loc[i, 'CHOSEN SERVICES'] = 'TRANSIT:WALK ' + 'TRAMLayer:TRAM ' * path.count('TRAM') + 'TRANSIT:WALK'
    if 'MOBILITY SERVICES' not in demand_data.columns:
        demand_data['MOBILITY SERVICES'] = 'METRO TRAM BUS'
    demand_data.to_csv(demand_file, sep=';', index=False)


if __name__ == '__main__':
    NX = 10
    NY = 10
    DIST_CONNECTION = 1e2

    mmgraph = load_graph(indir + "/lyon_network_gtfs_mod.json")
    odlayer = generate_bbox_origin_destination_layer(mmgraph.roads, NX, NY)
    mmgraph.add_origin_destination_layer(odlayer)
    mmgraph.connect_origindestination_layers(100, 1000)

    # if not os.path.exists(indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json"):
    #     mmgraph.connect_origin_destination_layer(DIST_CONNECTION)
    #     save_transit_link_odlayer(mmgraph, indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json")
    # else:
    #     load_transit_links(mmgraph, indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json")

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

    demand_file_name = indir + "/demandes.csv"
    force_public_transport(demand_file_name)
    demand = CSVDemandManager(demand_file_name)
    demand.add_user_observer(CSVUserObserver(outdir + "/user.csv"), user_ids="all")

    flow_motor = MFDFlowMotor(outfile=outdir + "/flow.csv")
    flow_motor.add_reservoir(Reservoir(mmgraph.roads.zones["RES"], ["CAR"], calculate_V_MFD))

    travel_decision = LogitDecisionModel(mmgraph, outfile=outdir + "/path.csv")

    supervisor = Supervisor(graph=mmgraph,
                            flow_motor=flow_motor,
                            demand=demand,
                            decision_model=travel_decision,
                            outfile=outdir + "/travel_time_link.csv")

    supervisor.run(Time('7:30:00'), Time('8:45:00'), Dt(seconds=30), 10)
