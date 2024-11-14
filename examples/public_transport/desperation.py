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

import pandas as pd

indir = "INPUTS"
outdir = "OUTPUTS"

# set_all_mnms_logger_level(LOGLEVEL.WARNING)
set_mnms_logger_level(LOGLEVEL.INFO, ["mnms.simulation"])

#get_logger("mnms.graph.shortest_path").setLevel(LOGLEVEL.WARNING)
attach_log_file(outdir+'/simulation.log')

# 'DESTINATION_R_82604106' 'ORIGIN_E_83202447'

def calculate_V_MFD(acc):
    #V = 10.3*(1-N/57000) # data from fit prop
    V = 0 # data from fit dsty
    N = acc["CAR"]
    if N<18000:
        V=11.5-N*6/18000
    elif N<55000:
        V=11.5-6 - (N-18000)*4.5/(55000-18000)
    elif N<80000:
        V= 11.5-6-4.5-(N-55000)*1/(80000-55000)
    #V = 11.5*(1-N/60000)
    V = max(V,0.001) # min speed to avoid gridlock
    V_TRAM_BUS = 0.7 * V
    return {"CAR": V, "METRO": 17, "BUS": V_TRAM_BUS, "TRAM": V_TRAM_BUS}


if __name__ == '__main__':
    NX = 10
    NY = 10
    DIST_CONNECTION = 1e2

    mmgraph = load_graph(indir + "/lyon_mnms_gtfs.json")

    odlayer = generate_bbox_origin_destination_layer(mmgraph.roads, NX, NY)

    mmgraph.add_origin_destination_layer(odlayer)

    mmgraph.connect_origindestination_layers(100,1000)

    # if not os.path.exists(indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json"):
    #     mmgraph.connect_origin_destination_layer(DIST_CONNECTION)
    #     save_transit_link_odlayer(mmgraph, indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json")
    # else:
    #     load_transit_links(mmgraph, indir + f"/transit_link_{NX}_{NY}_{DIST_CONNECTION}_grid.json")

    personal_car = PersonalMobilityService()
    personal_car.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["CAR"].add_mobility_service(personal_car)

    bus_service = PublicTransportMobilityService("BUS")
    bus_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["BUSLayer"].add_mobility_service(bus_service)

    tram_service = PublicTransportMobilityService("TRAM")
    tram_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["TRAMLayer"].add_mobility_service(tram_service)

    metro_service = PublicTransportMobilityService("METRO")
    metro_service.attach_vehicle_observer(CSVVehicleObserver(outdir + "/veh.csv"))
    mmgraph.layers["METROLayer"].add_mobility_service(metro_service)

    demand_file_name = indir + "/fichier_demandes.csv"
    demand = CSVDemandManager(demand_file_name)
    demand.add_user_observer(CSVUserObserver(outdir+"/user.csv"), user_ids="all")

    flow_motor = MFDFlowMotor(outfile=outdir+"/flow.csv")
    flow_motor.add_reservoir(Reservoir(mmgraph.roads.zones["RES"], ["CAR"], calculate_V_MFD))

    travel_decision = LogitDecisionModel(mmgraph, outfile=outdir+"/path.csv")

    supervisor = Supervisor(graph=mmgraph,
                            flow_motor=flow_motor,
                            demand=demand,
                            decision_model=travel_decision,
                            outfile=outdir + "/travel_time_link.csv")

    supervisor.run(Time('06:30:00'), Time('6:45:00'), Dt(minutes=1), 10)
