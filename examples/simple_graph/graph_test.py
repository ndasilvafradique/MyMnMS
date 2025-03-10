###############
### Imports ###
###############
## Casuals
import pathlib
import pickle

from mnms.graph.road import RoadDescriptor
from mnms.graph.zone import Zone
## MnMS
from mnms.log import set_all_mnms_logger_level, LOGLEVEL
from mnms.demand import CSVDemandManager
from mnms.flow.MFD import Reservoir, MFDFlowMotor
from mnms.generation.layers import generate_matching_origin_destination_layer, generate_layer_from_roads
from mnms.generation.roads import generate_line_road
from mnms.graph.layers import PublicTransportLayer, MultiLayerGraph
from mnms.io.graph import save_graph
from mnms.mobility_service.public_transport import PublicTransportMobilityService
from mnms.simple_simulation import Supervisor
from mnms.time import TimeTable, Time, Dt
from mnms.tools.observer import CSVUserObserver, CSVVehicleObserver
from mnms.travel_decision.custom_decision_model import BCDecisionModel
from mnms.vehicles.veh_type import Bus, Metro, Tram
from mnms.io.graph import load_graph, load_odlayer, save_graph, save_odlayer, save_transit_link_odlayer, \
    load_transit_links

import os
import shutil


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


def rename_outputs_dir(baseline=True):
    """Renames the 'OUTPUTS' directory to 'BASELINE' or 'TEST' based on the 'baseline' flag.

    Args:
        baseline (bool): If True, renames to 'BASELINE'; otherwise, renames to 'TEST'.
    """

    outputs_dir = "OUTPUTS"
    new_dir_name = "BASELINE" if baseline else "TEST"

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


def print_graph(mlgraph):
    f = open('costs.out', 'w')
    link_layers = list()

    for lid, layer in mlgraph.layers.items():
        link_layers.append(layer.graph.links)  # only non transit links concerned

    for link in mlgraph.graph.links.values():
        costs = {}
        if link.label == "TRANSIT":
            speed = walk_speed
            costs["WALK"] = {"speed": speed,
                             "travel_time": link.length / speed,
                             "length": link.length}
            travel_time = link.length / speed
            if travel_time > 0:
                f.write(f'{link.label}, {link.upstream}, {link.downstream}, {costs}\n')
        else:
            layer = mlgraph.layers[link.label]
            speed = layer.default_speed
            for mservice in layer.mobility_services.keys():
                costs[mservice] = {"speed": speed,
                                   "travel_time": link.length / speed,
                                   "length": link.length}
                travel_time = link.length / speed
                if travel_time > 0:
                    f.write(f'{link.label}, {link.upstream}, {link.downstream}, {costs}\n')


def get_stations(mlgraph):
    stations = set()
    for link in mlgraph.graph.links.values():
        if link.label != "TRANSIT":
            stations.add(link.upstream)
            stations.add(link.downstream)
    return stations


# def create_demand(filename, n_users=1):
#     with open(filename, 'w') as f:
#         f.write(f'ID;DEPARTURE;ORIGIN;DESTINATION;MOBILITY SERVICE\n')
#         min = 1
#         for i in range(n_users):
#             if i % 10 == 0:
#                 min = min + 2
#             f.write(f'U{i};07:{min:02}:00;0 0;3000 0;TRAM METRO BUS\n')
#

# def create_demand(filename, tstart_user, tstart_ghost, n_users=1, ghost_users=20):
#     with open(filename, 'w') as f:
#         f.write(f'ID;DEPARTURE;ORIGIN;DESTINATION;MOBILITY SERVICE\n')
#         for min in range(0, 60, 2):
#             for i in range(ghost_users):
#                 f.write(f'GHOST{i}_{min};06:{min}:00;0 0;3000 0;TRAM METRO BUS\n')
#
#         for i in range(0, n_users):
#             f.write(f'U{i};{tstart_user};0 0;3000 0;TRAM METRO BUS\n')


ensure_outputs_dir()

##################
### Parameters ###
##################
log_file = pathlib.Path('sim.log').resolve()
walk_speed = 1.4  # m/s
bus_speed = 8.5  # m/s
tram_speed = 8.5  # m/s
metro_speed = 11  # m/s
bus_frequency = Dt(minutes=15)
metro_frequency = Dt(minutes=5)
tram_frequency = Dt(minutes=10)

tstart = "06:30:00"
tend = "07:00:00"
dt_flow = Dt(minutes=1)
odlayer_connection_dist = 215  # m


def mfdspeed(dacc):
    dacc['BUS'] = bus_speed  # m/s
    dacc['METRO'] = metro_speed  # m/s
    dacc['TRAM'] = metro_speed
    return dacc


#########################
### Scenario creation ###
#########################

#### RoadDescriptor ####
roads = generate_line_road([0, 0], [3000, 0], 2)
roads.register_stop('SO', '0_1', 0.1)
roads.register_stop('S1', '0_1', 0.3)
roads.register_stop('S2', '0_1', 0.5)
roads.register_stop('S3', '0_1', 0.7)
roads.register_stop('S4', '0_1', 0.9)

roads_1 = generate_line_road([0, 50], [3000, 50], 2)
roads_1.register_stop('S5', '0_1', 0.1)
roads_1.register_stop('S6', '0_1', 0.4)
roads_1.register_stop('S3', '0_1', 0.7)
roads_1.register_stop('S7', '0_1', 0.9)

# Combine RoadDescriptors into a single RoadDescriptor
combined_roads = RoadDescriptor()
combined_roads.nodes.update(roads.nodes)
combined_roads.nodes.update(roads_1.nodes)
combined_roads.sections.update(roads.sections)
combined_roads.sections.update(roads_1.sections)
combined_roads.stops.update(roads.stops)
combined_roads.stops.update(roads_1.stops)
zone_res = Zone('RES', set(['0_1']), [])  #example zone with section 0_1, and no contour.
combined_roads.add_zone(zone_res)

#### Public Transport Layers ####
capacity_info = {'BUS': 30, 'BUS_1': 30, 'METRO': 150, 'TRAM': 70}

bus_service = PublicTransportMobilityService('BUS', capacity_info=capacity_info)
bus_layer = PublicTransportLayer(combined_roads, 'BUS', Bus, bus_speed, services=[bus_service],
                                 observer=CSVVehicleObserver("OUTPUTS/bus_vehs.csv"))
metro_service = PublicTransportMobilityService('METRO', capacity_info=capacity_info)
metro_layer = PublicTransportLayer(combined_roads, 'METRO', Metro, metro_speed, services=[metro_service],
                                   observer=CSVVehicleObserver("OUTPUTS/metro_vehs.csv"))

tram_service = PublicTransportMobilityService('TRAM', capacity_info=capacity_info)
tram_layer = PublicTransportLayer(combined_roads, 'TRAM', Tram, tram_speed, services=[tram_service],
                                  observer=CSVVehicleObserver("OUTPUTS/tram_vehs.csv"))

bus_layer.create_line('BUS',
                      ['SO', 'S1', 'S2', 'S3', 'S4'],
                      [['0_1'], ['0_1'], ['0_1'], ['0_1']],
                      TimeTable.create_table_freq('00:00:00', tend, bus_frequency))

bus_layer.create_line('BUS_1',
                      ['S5', 'S6', 'S3', 'S7'],
                      [['0_1'], ['0_1'], ['0_1']],
                      TimeTable.create_table_freq('00:00:00', tend, bus_frequency))

metro_layer.create_line('METRO',
                        ['SO', 'S2', 'S4'],  # Metro has fewer stops
                        [['0_1'], ['0_1']],
                        TimeTable.create_table_freq('00:00:00', tend, metro_frequency))

tram_layer.create_line('TRAM',
                       ['SO', 'S1', 'S2', 'S3', 'S4'],  # Metro has fewer stops
                       [['0_1'], ['0_1'], ['0_1'], ['0_1']],
                       TimeTable.create_table_freq('00:00:00', tend, tram_frequency))

# Create origin-destination layer
odlayer = generate_matching_origin_destination_layer(roads)
mlgraph = MultiLayerGraph([bus_layer, metro_layer, tram_layer], odlayer, 500)
mlgraph.connect_inter_layers(['BUS', 'METRO', 'TRAM'], 500)
mlgraph.connect_intra_layer('BUS', 500)
mlgraph.connect_intra_layer('METRO', 500)
mlgraph.connect_intra_layer('TRAM', 500)

mlgraph.initialize_costs(walk_speed)

# Connect layers with intermodal transfers
save_graph(mlgraph, 'test_mlgraph.json')
save_transit_link_odlayer(mlgraph, 'test_transit_link.json', 4)
print_graph(mlgraph)

#### Demand ####
demand_file = pathlib.Path('morning_peak_demand.csv').resolve()
demand = CSVDemandManager(demand_file)
demand.add_user_observer(CSVUserObserver('OUTPUTS/users.csv'))
stations = get_stations(mlgraph)
with open('stations.pkl', 'wb') as f:
    pickle.dump(stations, f)
print(stations)

#### Flow Motor ####
flow_motor = MFDFlowMotor()
flow_motor.add_reservoir(Reservoir(roads.zones['RES'], ['BUS', 'METRO', 'TRAM'], mfdspeed))

baseline = False
travel_decision = BCDecisionModel(mlgraph, outfile="OUTPUTS/path.csv",
                                  baseline=baseline, top_k=3, n_shortest_path=10,
                                  max_diff_cost=1.00,
                                  max_dist_in_common=0.98,
                                  cost_multiplier_to_find_k_paths=1.1,
                                  behavior_file='user_travel_profiles_total_visits.csv')

#### Supervisor ####
supervisor = Supervisor(mlgraph, demand, flow_motor, travel_decision, logfile=log_file, loglevel=LOGLEVEL.INFO)

######################
### Run Simulation ###
######################
set_all_mnms_logger_level(LOGLEVEL.INFO)
supervisor.run(Time(tstart), Time(tend), dt_flow, affectation_factor=1)
rename_outputs_dir(baseline)
