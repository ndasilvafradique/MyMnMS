import os

import pandas as pd


class CongestionModel:
    """
    A singleton class representing a congestion model.
    """

    __instance = None  # Private class variable to hold the instance

    def __init__(self, prediction_technique):
        """
        Private initializer. Prevents direct instantiation.
        """
        if CongestionModel.__instance is not None:
            raise Exception("CongestionModel is a singleton. Use get_instance() instead.")
        else:
            self.prediction_technique = prediction_technique
            self.data = pd.DataFrame(columns=['TIMESTAMP', 'VEHICLE ID', 'PASSENGERS', 'CAPACITY', 'CONGESTION INDEX', 'NODE'])

    @staticmethod
    def get_instance(prediction_technique=('temporal_moving_avg', {'window':60})):
        """
        Static method to get the singleton instance.
        Creates the instance if it doesn't exist.
        """
        if CongestionModel.__instance is None:
            CongestionModel.__instance = CongestionModel(prediction_technique)
        return CongestionModel.__instance

    def update_congestion_model(self, new_data):
        next_row = pd.DataFrame.from_dict(new_data)  # Create a DataFrame from the dictionary
        self.data = pd.concat([self.data, next_row], ignore_index=True)  # Concatenate with existing DataFrame

    def temporal_moving_average(self, data, window):
        return data.rolling(window=window).mean()

    def predict_congestion(self, node):
        CI = self.data[self.data['NODE'] == node]

        # If no data is available for the node, return 0
        if CI.empty:
            return 0

        # Apply temporal moving average if technique is specified
        if self.prediction_technique[0] == 'temporal_moving_avg':
            window = self.prediction_technique[1].get('window', 1)  # Default to window=1 if not provided
            # Compute rolling mean
            CI['CONGESTION INDEX MA'] = CI['CONGESTION INDEX'].rolling(window=window).mean()
            return CI['CONGESTION INDEX MA'].iloc[-1]

        # Default return if no technique applies
        return CI['CONGESTION INDEX'].iloc[-1]

    def clear_data(self):
        """
        Clears all congestion data.
        """
        self.data.clear()

    def write_congestion(self, path):
        self.data.to_csv(f'{path}{os.sep}congestion_history.csv')
