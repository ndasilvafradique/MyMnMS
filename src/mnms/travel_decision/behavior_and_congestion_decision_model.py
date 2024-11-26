import logging
from math import exp, fsum
from typing import List, Tuple

import numpy as np

from mnms import create_logger
from mnms.demand.user import Path
from mnms.travel_decision.abstract import AbstractDecisionModel
from mnms.graph.layers import MultiLayerGraph
import pandas as pd

log = create_logger(__name__)


class BehaviorCongestionDecisionModel(AbstractDecisionModel):
    def __init__(self, mmgraph: MultiLayerGraph, considered_modes=None, cost='travel_time', outfile:str=None, verbose_file=False):
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
                                                )
        self._seed = None
        self._rng = None
        self.CI_data = pd.read_csv('OUTPUTS/congestion_file_backup.csv')


    def set_random_seed(self, seed):
        """Method that sets the random seed for this decision model.

        Args:
            -seed: seed as an integer
        """
        if seed is not None:
            self._seed = seed
            rng = np.random.default_rng(self._seed)
            self._rng = rng

    def path_choice(self, paths:List[Path], tcurrent) -> Path:
        """Method that proceeds to the selection of the path.

        Args:
            -paths: list of paths to consider for the choice

        Returns:
            -selected_path: path chosen
        """
        path_selected = None
        path_score = []

        # base cost
        for path in paths:
            print(path.nodes)
            score = [(1 - self.get_CI(x, tcurrent)) + self.get_BI(x, tcurrent) + (1-self.get_C(x, tcurrent)) for x in path.nodes]
            path_score.append(score)

        return path_selected[np.argmax(path_score)]


    def get_CI(self, node, tcurrent):
        CI = self.CI_data[(self.CI_data['NODE'] == node) & (self.CI_data['TIMESTAMP'] == tcurrent)]
        return CI

    def get_BI(self, node, tcurrent):
        return 1

    def get_C(self, node, tcurrent):
        '''TO DO'''
        return 1
