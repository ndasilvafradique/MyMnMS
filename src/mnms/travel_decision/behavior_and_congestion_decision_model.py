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

log = create_logger(__name__)


class BehaviorCongestionDecisionModel(AbstractDecisionModel):
    def __init__(self, mmgraph: MultiLayerGraph, considered_modes=None, cost='travel_time', outfile: str = None,
                 verbose_file=False, alpha=1):
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
                                                              alpha=alpha
                                                              )
        self._seed = None
        self._rng = None
        self.alpha = alpha
        assert cost == 'travel_time'
        self.CI_data = pd.read_csv('OUTPUTS/congestion_file_backup.csv')
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

    def path_choice(self, paths: List[Path], tcurrent) -> Path:
        """Method that proceeds to the selection of the path.

        Args:
            -paths: list of paths to consider for the choice

        Returns:
            -selected_path: path chosen
        """
        path_score = []

        # EXTRACT THE LONGEST LINK AMONG ALL PATHS
        max_cost = 0
        for path in paths:
            path_tt = path.link_cost.values()
            longest_link = np.max(path_tt)
            if longest_link > max_cost:
                max_cost = longest_link

        # base cost
        for path in paths:
            score = 0
            path_tt = path.link_cost.values()
            # EXCLUDE THE ORIGIN AND DESTINAION FROM COMPUTATION
            i = 0
            line = paths.nodes[1].split('_')[0]
            for x in paths.nodes[1:-1]:
                next_line = x.split('_')[0] + x.split('_')[1]
                if line != next_line or i == 0:
                    t = sum(path_tt[:i]) + tcurrent
                    line = next_line
                    score += self.alpha * (1 - self.get_CI(x, t)) + (1 - self.alpha) * self.get_BI(x, t)
                # TO CHECK
                C = path.link_cost[x] / max_cost
                score += C
                i += 1
            path_score.append(score)

        return paths[np.argmax(path_score)] if len(path_score) > 0 else None

    def get_CI(self, node, tcurrent):
        CI = self.CI_data[self.CI_data['NODE'] == node].copy(deep=True)
        tcurrent_datetime = pd.to_datetime(str(tcurrent))
        CI['time_diff'] = [(x - tcurrent_datetime).total_seconds() for x in CI.TIMESTAMP]
        CI = CI[CI['time_diff'] >= 0]
        CI = CI.sort_values(by=['time_diff', 'CONGESTION INDEX']).reset_index(drop=True, inplace=False)
        print('node', node, tcurrent, CI.loc[0, 'CONGESTION INDEX'])
        return CI['CONGESTION INDEX'][0]

    def get_BI(self, x, tcurrent):
        return 1
