import logging
from math import exp, fsum
from typing import List, Tuple

import numpy as np

from mnms import create_logger
from mnms.congestion_model import CongestionModel
from mnms.demand.user import Path
from mnms.time import Time
from mnms.travel_decision.abstract import AbstractDecisionModel
from mnms.graph.layers import MultiLayerGraph
import pandas as pd
import redis
from datetime import datetime, timedelta
import time
import re
import hashlib


log = create_logger(__name__)


class BehaviorCongestionDecisionModel(AbstractDecisionModel):
    def __init__(self, mmgraph: MultiLayerGraph, considered_modes=None, cost='travel_time', outfile: str = None,
                 verbose_file=False, alpha=1, beta=1, gamma=1,
                 baseline=False, top_k=3, n_shortest_path=10,
                 congestion_prediction_technique=None,
                 max_diff_cost: float = 0.25,
                 max_dist_in_common: float = 0.95,
                 cost_multiplier_to_find_k_paths: float = 10,
                 ):
        """Behavior- and congestion-driven decision model for the path of a user.
        All routes computed are considered on an equal footing for the choice.

        Args:
            -mmgraph: The graph on which the model compute the path
            -considered_modes: List of guidelines for the guided paths discovery,
                           if None, the default paths discovery is applied
            -cost: name of the cost to consider
            -outfile: Path to result CSV file, nothing is written if None
            -verbose_file: If True write all the computed shortest path, not only the one that is selected
            -personal_mob_service_park_radius: radius around user's personal veh parking location in which
                                               she can still have access to her vehicle
            -save_routes_dynamically_and_reapply: boolean specifying if the k shortest paths computed
                                                  for an origin, destination, and mode should be saved
                                                  dynamically and reapply for next departing users with
                                                  the same origin, destination and mode
        """
        super(BehaviorCongestionDecisionModel, self).__init__(mmgraph,
                                                              considered_modes=considered_modes,
                                                              cost=cost,
                                                              outfile=outfile,
                                                              verbose_file=verbose_file,
                                                              n_shortest_path=n_shortest_path,
                                                              save_routes_dynamically_and_reapply=True,
                                                              max_diff_cost=max_diff_cost,
                                                              max_dist_in_common=max_dist_in_common,
                                                              cost_multiplier_to_find_k_paths=cost_multiplier_to_find_k_paths,
                                                              )
        # Connect to Redis (adjust host and port)
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)
        self._seed = None
        self._rng = None
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.baseline = baseline
        self.top_k = top_k
        assert cost == 'travel_time'
        self.congestion_prediction_technique = congestion_prediction_technique
        self.baseline = baseline

        # self.CI_data = pd.read_csv(congestion_file_path)
        # self.CI_data.TIMESTAMP = pd.to_datetime(self.CI_data.TIMESTAMP, format='mixed')

    def set_random_seed(self, seed):
        """Method that sets the random seed for this decision model.

        Args:
            -seed: seed as an integer
        """
        if seed is not None:
            self._seed = seed
            rng = np.random.default_rng(self._seed)
            self._rng = rng

    def path_choice(self, paths: List[Path], uid, tcurrent=None) -> Path:
        """Method that proceeds to the selection of the path.

        Args:
            -paths: list of paths to consider for the choice

        Returns:
            -selected_path: path chosen
        """
        print('N PATHS:', len(paths), 'found for user', uid)
        paths_ID = dict()
        for i in range(len(paths)):
            p_hash = self.get_path_hash(paths[i])
            paths_ID[p_hash] = paths[i]

        the_chosen_one = None

        if len(paths) > 1:
            cost_score = [p.path_cost for p in paths]
            CI_score = [0 for i in range(len(paths))]
            BI_score = [0 for i in range(len(paths))]
            line_changes = [0] * len(paths)

            for p in range(len(paths)):
                path_tt = paths[p].get_link_cost(self._mlgraph, self._cost)
                services = paths[p].mobility_services
                services = [item for item in services if item != 'WALK']
                print('PATH MOB SERVICES', services)
                line_changes[p] = len(services) - 1
                print('PATH COST ANALYSIS: ', sum(path_tt), paths[p].get_link_cost(self._mlgraph, self._cost))
                # EXCLUDE THE ORIGIN AND DESTINAION FROM COMPUTATION
                i = 0
                x = paths[p].nodes[1]
                if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                    line = x.split('_')[0] + x.split('_')[1]
                else:
                    line = ''
                for x in paths[p].nodes[1:-1]:
                    if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                        next_line = x.split('_')[0] #+ x.split('_')[1]
                        if line != next_line or i == 0:
                            line = next_line
                            # This control is useful when an user crosses a station without taking
                            # the related mobility services
                            if len(services) and next_line == services[0]:
                                    services = services[1:]
                                    t = timedelta(seconds=sum(path_tt[:i])) + datetime.strptime(str(tcurrent),'%H:%M:%S.%f')
                                    t = datetime.strptime(str(tcurrent), '%H:%M:%S.%f') - timedelta(seconds=30)
                                    print('TIME DEBUG: ', str(tcurrent), sum(path_tt[:i]), t)
                                    CI_score[p] += self.get_CI(t, x, line)
                                    BI_score[p] += self.get_BI(uid, x, t)
                    i += 1
                print('')

            ranked_paths = pd.DataFrame({'ID': paths_ID.keys(), 'CI': CI_score, 'BI': BI_score, 'cost': cost_score,
                                         'line_changes': line_changes})

            # Sort the paths in ascending or descending order based on the criterion's nature. For example:
            # Congestion Index: Lower is better (ascending order).
            # Behavior Index (Preference): Higher is better (descending order).
            # Cost (in Time): Lower is better (ascending order).
            # Line Changes: Lower is better (ascending order).

            ranked_paths["CongestionRank"] = ranked_paths["CI"].rank(ascending=True)
            ranked_paths["BehaviorRank"] = ranked_paths["BI"].rank(ascending=False)
            ranked_paths["CostRank"] = ranked_paths["cost"].rank(ascending=True)
            ranked_paths["LineChangesRank"] = ranked_paths["line_changes"].rank(ascending=True)

            if self.baseline:
                # Calculate total score
                ranked_paths["TotalRank"] = (
                        ranked_paths["BehaviorRank"] +
                        ranked_paths["CostRank"] +
                        ranked_paths["LineChangesRank"]
                )

                ranked_paths.drop(columns=['CongestionRank', 'CI'], inplace=True)
                ranked_paths = ranked_paths.sort_values(by="TotalRank", ascending=True)
            else:
                # Select the best k path based on behavior rank
                ranked_paths = ranked_paths.nsmallest(self.top_k, "BehaviorRank")

                # Calculate total score on the other criteria
                ranked_paths["TotalRank"] = (
                        ranked_paths["CongestionRank"] +
                        ranked_paths["BehaviorRank"] +
                        ranked_paths["CostRank"] +
                        ranked_paths["LineChangesRank"] #+
                )

                # Sort by total score
                ranked_paths = ranked_paths.sort_values(by="TotalRank", ascending=True)

            # ranked_to_print = ranked_paths.copy(deep=True)
            # ranked_to_print['USER'] = [uid] * len(ranked_paths)
            # ranked_to_print['DEPARTURE'] = [tcurrent] * len(ranked_paths)
            # ranked_to_print['SERVICES'] = [paths_ID[p].mobility_services for p in ranked_to_print['ID']]
            # ranked_to_print['NODES'] = [paths_ID[p].nodes for p in ranked_to_print['ID']]

            for key, value in paths_ID.items():
                print(key, value.nodes)

            # if 'U' in uid:
            #     ranked_to_print.to_csv(f'OUTPUTS/rank_{uid}_{str(tcurrent).replace(":", "_")}.csv', index=False)

            the_chosen_one = paths_ID[ranked_paths.iloc[0, 0]]

            print(f'User {uid} will chose path: ', ranked_paths.iloc[0, 0])
            print('Departure at: ', tcurrent)
            print('*'*100)

        elif len(paths) == 1:
            p_hash = self.get_path_hash(paths[0])
            the_chosen_one =  paths[0]

        return the_chosen_one

    def get_path_hash(self, path):
        stations = path.nodes[1:-1]
        path_string = " ".join(stations)  # Create a comma-separated string
        encoded_string = path_string.encode('utf-8')  # Encode to bytes
        hash_object = hashlib.sha256(encoded_string)
        hex_hash = hash_object.hexdigest()
        return hex_hash

    def get_CI(self, node):
        return CongestionModel.get_instance(self.congestion_prediction_technique).predict_congestion(node)
        # print(node, tcurrent)
        # CI = self.CI_data[self.CI_data['NODE'] == node].copy(deep=True)
        # if len(CI) == 0:
        #     return 0
        # else:
        #     # tcurrent_datetime = pd.to_datetime(str(tcurrent))
        #     # CI['time_diff'] = [(x - tcurrent_datetime).total_seconds() for x in CI.TIMESTAMP]
        #     # CI = CI[CI['time_diff'] >= 0]
        #     # CI = CI.sort_values(by=['time_diff', 'CONGESTION INDEX']).reset_index(drop=True, inplace=False)
        #     # if len(CI) == 0:
        #     #     return 0
        #     # else:
        #     #     print('node', node, tcurrent, CI.loc[0, 'CONGESTION INDEX'])
        #     #     return CI['CONGESTION INDEX'][0]
        #     window = 60
        #     CI = self.simple_moving_average(CI['CONGESTION INDEX'], window)
        #     print('CI', tcurrent)
        #     return CI

    def get_BI(self, uid, x, tcurrent):
        user = uid
        bin = self.get_current_time_bin(tcurrent)
        target = f'{self.clean_route(x)}-{bin}'

        BI_value = self.redis_client.hget(user, target)
        if BI_value is None:
            BI_value = 0
        print('BI', BI_value)
        return float(BI_value)

    def get_current_time_bin(self, tcurrent, bin_minutes=10):
        # Calculate the start of the bin
        bin_start = tcurrent - timedelta(minutes=tcurrent.minute % bin_minutes, seconds=tcurrent.second,
                                         microseconds=tcurrent.microsecond)
        return bin_start.strftime("%H:%M")

    def clean_route(self, route):
        # Rimuove tutto ciò che si trova tra due occorrenze di DIRx (incluso DIRx)
        route = re.sub(r'_DIR\d+.*?_DIR\d+', '', route, flags=re.IGNORECASE)
        # Converte tutto in maiuscolo
        route = route.upper()
        return route
