import logging
from math import exp, fsum
from typing import List, Tuple

import numpy as np

from mnms import create_logger
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
                 verbose_file=False, alpha=1, beta=1, gamma=1):
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
                                                              #alpha=alpha,
                                                              #beta=beta,
                                                              #gamma=gamma
                                                              )
        # Connect to Redis (adjust host and port)
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

        self._seed = None
        self._rng = None
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        assert cost == 'travel_time'
        #if self.alpha != 0:
        self.CI_data = pd.read_csv('OUTPUTS/congestion_cost.csv')
        self.CI_data.TIMESTAMP = pd.to_datetime(self.CI_data.TIMESTAMP, format='mixed')

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
        path_score = []
        
        # EXTRACT THE LONGEST PATH AMONG ALL PATHS
        max_path_cost = 0
        for path in paths:
            path_cost = path.path_cost
            if path_cost > max_path_cost:
                max_path_cost = path_cost
                

        # base cost
        for path in paths:
            score = 0
            path_tt = path.get_link_cost(self._mlgraph, self._cost)
            # EXCLUDE THE ORIGIN AND DESTINAION FROM COMPUTATION
            i = 0
            line_changes = 1
            if self.alpha != 0 or self.beta != 0:
                x = path.nodes[1]
                # Get line ID. Ex. TRAMT5
                if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                    line = x.split('_')[0] + x.split('_')[1]
                else:
                    line = ''
                for x in path.nodes[1:-1]:
                    print('X', x)
                    if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                        next_line = x.split('_')[0] + x.split('_')[1]
                        if line != next_line or i == 0:
                            t = timedelta(seconds=sum(path_tt[:i])) + datetime.strptime(str(tcurrent), '%H:%M:%S.%f')
                            print(str(tcurrent), sum(path_tt[:i]), t)
                            line = next_line
                            score += self.alpha * (1 - self.get_CI(x, t)) + self.beta * self.get_BI(uid, x, t)
                            if i != 0:
                                line_changes = line_changes + 1
                    i += 1
                score = score/line_changes
            C = path.path_cost / max_path_cost
            score += self.gamma * (1 - C)
            path_score.append(score)

        return paths[np.argmax(path_score)] if len(path_score) > 0 else None

    def get_CI(self, node, tcurrent):
        print(node, tcurrent)
        CI = self.CI_data[self.CI_data['NODE'] == node].copy(deep=True)
        if len(CI) == 0:
            return 0
        tcurrent_datetime = pd.to_datetime(str(tcurrent))
        CI['time_diff'] = [(x - tcurrent_datetime).total_seconds() for x in CI.TIMESTAMP]
        CI = CI[CI['time_diff'] >= 0]
        CI = CI.sort_values(by=['time_diff', 'CONGESTION INDEX']).reset_index(drop=True, inplace=False)
        if len(CI) == 0:
            return 0
        else:
            print('node', node, tcurrent, CI.loc[0, 'CONGESTION INDEX'])
            return CI['CONGESTION INDEX'][0]

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
        bin_start = tcurrent - timedelta(minutes=tcurrent.minute % bin_minutes, seconds=tcurrent.second, microseconds=tcurrent.microsecond)
        return bin_start.strftime("%H:%M")

    def clean_route(self, route):
        # Rimuove tutto ciò che si trova tra due occorrenze di DIRx (incluso DIRx)
        route = re.sub(r'_DIR\d+.*?_DIR\d+', '', route, flags=re.IGNORECASE)
        # Converte tutto in maiuscolo
        route = route.upper()
        return route