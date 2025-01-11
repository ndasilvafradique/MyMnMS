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

log = create_logger(__name__)


class BehaviorCongestionDecisionModel(AbstractDecisionModel):
    def __init__(self, mmgraph: MultiLayerGraph, considered_modes=None, cost='travel_time', outfile: str = None,
                 verbose_file=False, alpha=1, beta=1, gamma=1,
                 baseline=False, top_k=3, n_shortest_path=10,
                 congestion_prediction_technique=None):
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
                                                              n_shortest_path=n_shortest_path
                                                              )
        # Connect to Redis (adjust host and port)
        # self.redis_client = redis.StrictRedis(host='http://137.121.170.69',
        #                                      port=6379, decode_responses=True)

        self._seed = None
        self._rng = None
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.baseline = baseline
        self.top_k = top_k
        assert cost == 'travel_time'
        self.congestion_prediction_technique = congestion_prediction_technique
        #self.CI_data = pd.read_csv(congestion_file_path)
        #self.CI_data.TIMESTAMP = pd.to_datetime(self.CI_data.TIMESTAMP, format='mixed')

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
        print('N PATHS:', len(paths))
        if len(paths) > 1:
            cost_score = [p.path_cost for p in paths]
            CI_score = [0 for i in range(len(paths))]
            BI_score = [0 for i in range(len(paths))]

            for p in range(len(paths)):
                path_tt = paths[p].get_link_cost(self._mlgraph, self._cost)
                # EXCLUDE THE ORIGIN AND DESTINAION FROM COMPUTATION
                i = 0
                line_changes = 1
                if self.alpha != 0 or self.beta != 0:
                    x = paths[p].nodes[1]
                    # Get line ID. Ex. TRAMT5
                    if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                        line = x.split('_')[0] + x.split('_')[1]
                    else:
                        line = ''
                    for x in paths[p].nodes[1:-1]:
                        print('X', x)
                        if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                            next_line = x.split('_')[0] + x.split('_')[1]
                            if line != next_line or i == 0:
                                t = timedelta(seconds=sum(path_tt[:i])) + datetime.strptime(str(tcurrent),
                                                                                            '%H:%M:%S.%f')
                                #t = datetime.strptime(str(tcurrent), '%H:%M:%S.%f') - timedelta(seconds=30)
                                #print(str(tcurrent), sum(path_tt[:i]), t)
                                line = next_line
                                CI_score[p] += self.get_CI(x)
                                #BI_score[p] += self.get_BI(uid, x, t)
                                if i != 0:
                                    line_changes = line_changes + 1
                        i += 1
                    CI_score[p] = self.alpha * CI_score[p] / line_changes
                    #BI_score[p] = self.beta * BI_score[p] / line_changes

            if self.baseline:
                criteria = {'BI': (BI_score, True), 'C': (cost_score, False)}
            else:
                criteria = {'CI': (CI_score, False), 'BI': (BI_score, True), 'C': (cost_score, False)}
            # CREATE C RANKS AND SORT PATH. THEN COMBINE THE SCORE BASED ON VALUE AND POSITION WITHIN THE RANKS
            # AND GET THE TOP K
            ranked_paths = self.rank_paths(criteria, len(paths)).iloc[:self.top_k, :]
            random_path = ranked_paths.iloc[np.random.randint(low=0, high=len(ranked_paths)), 0]
            print('Path', random_path, paths)
            random_path = paths[random_path]
            return random_path
        elif len(paths) == 1:
            return paths[0]
        else:
            return None

    def rank_paths(self, criteria, P):
        rankings = [
            pd.DataFrame({'ID': list(range(P)), c: criteria[c][0]}).sort_values(by=c,
                                                                                ascending=criteria[c][1]).reset_index(
                drop=True)
            for c in criteria]
        ranked_paths = pd.DataFrame({'ID': list(range(P)), 'SCORE': [0.0] * P})

        for p in ranked_paths.index:
            for rank in rankings:
                path = rank[rank['ID'] == p]
                ranked_paths.iloc[p, 1] += (path.index[0] + 1)  # POSITION
        return ranked_paths

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
