import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

class TimetableGenerator:
    def __init__(self, mlgraph):
        self.mlgraph = mlgraph
        self.timetables = {}
        self.line_timetables = {}  # Dizionario per i DataFrame delle tabelle orarie complete
        self.generate_timetables()

    def generate_timetables(self):
        if not os.path.exists('timetables'):
            os.makedirs('timetables')
            for layer in self.mlgraph.layers:
                for line_name, line_data in self.mlgraph.layers[layer].lines.items():
                    print(f"Generating timetable for line: {line_name}")
                    nodes = line_data['nodes']
                    departure_times = line_data['table'].__dump__()
                    line_timetable_data = {}  # Dizionario per costruire il DataFrame della linea

                    for node in nodes:
                        line_timetable_data[node] = []  # Crea una lista vuota per ogni nodo

                    for departure_time in departure_times:
                        current_time = pd.to_datetime(departure_time)
                        line_timetable_data[nodes[0]].append(current_time) # aggiunge l'orario di partenza al capolinea.
                        for i in range(len(nodes) - 1):
                            current_node = nodes[i]
                            next_node = nodes[i + 1]
                            travel_time = self.mlgraph.graph.nodes[current_node].adj[next_node].costs[layer]['travel_time']
                            current_time += pd.Timedelta(seconds=travel_time)
                            line_timetable_data[next_node].append(current_time)

                    self.line_timetables[line_name] = pd.DataFrame(line_timetable_data)
                    self.line_timetables[line_name].index = pd.to_datetime(departure_times)
                    self.line_timetables[line_name].to_csv(f'timetables/{line_name}.csv')
        else:
            for filename in os.listdir('timetables'):
                line_name = filename.split('.')[0]
                data = pd.read_csv(f'timetables/{filename}')
                data.rename(columns={'Unnamed: 0': 'index'}, inplace=True)
                data.index = pd.to_datetime(data['index'])
                data.drop(columns=['index'], inplace=True)
                for col in data.columns:
                    data[col] = pd.to_datetime(data[col])
                self.line_timetables[line_name] = data

    def get_line_timetables(self):
        return self.line_timetables


class CongestionModel:
    """
    A singleton class representing a congestion model.
    """

    __instance = None  # Private class variable to hold the instance

    def __init__(self, mlgraph=None, model='moving_avg'):
        """
        Private initializer. Prevents direct instantiation.
        """
        if CongestionModel.__instance is not None:
            raise Exception("CongestionModel is a singleton. Use get_instance() instead.")
        else:
            if model == 'moving_avg':
                self.data = pd.DataFrame(columns=['TIMESTAMP', 'VEHICLE ID', 'PASSENGERS', 'CAPACITY', 'CONGESTION INDEX', 'NODE'])
            else:
                self.data = pd.DataFrame(columns=['TIMESTAMP', 'NODE', 'EXPECTED'])
                self.mlgraph = mlgraph
                self.timetables = TimetableGenerator(self.mlgraph).get_line_timetables()


    @staticmethod
    def get_instance(mlgraph=None, model='moving_avg'):
        """
        Static method to get the singleton instance.
        Creates the instance if it doesn't exist.
        """
        if CongestionModel.__instance is None:
            CongestionModel.__instance = CongestionModel(mlgraph, model)
        return CongestionModel.__instance

    def update_congestion_model_mavg(self, new_data, model='moving_avg'):
        if model == 'moving_avg':
            next_row = pd.DataFrame.from_dict(new_data)  # Create a DataFrame from the dictionary
            self.data = pd.concat([self.data, next_row], ignore_index=True)  # Concatenate with existing DataFrame

    def update_congestion_model(self, p, path_tt, tcurrent):
        i = 0
        x = p.nodes[1]
        if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
            line = x.split('_')[0] + x.split('_')[1]
        else:
            line = ''
        for x in p.nodes[1:-1]:
            if 'METRO' in x or 'TRAM' in x or 'BUS' in x:
                next_line = x.split('_')[0]  # + x.split('_')[1]
                if line != next_line or i == 0:
                    t = timedelta(seconds=sum(path_tt[:i])) + datetime.strptime(str(tcurrent), '%H:%M:%S.%f')
                    line = next_line
                    self.update_or_add(t, x, line)
            i += 1

    def align_to_next_departure(self, timestamp, node, line):
        timestamp = timestamp.strftime('%H:%M:%S')
        for next_departure in self.timetables[line][node]:
            if next_departure.strftime('%H:%M:%S') >= timestamp:
                break
        return next_departure

    def update_or_add(self, t, node, line):
        timestamp = pd.to_datetime(self.align_to_next_departure(t, node, line))

        key = (timestamp, node)
        existing_keys = list(zip(self.data['TIMESTAMP'], self.data['NODE']))
        if key in existing_keys:
            # Key exists, increment 'EXPECTED'
            index = existing_keys.index(key)
            value = self.data.loc[index, 'EXPECTED'] + 1
            self.data.loc[index, 'EXPECTED'] = value
        else:
            # Key doesn't exist, append the row
            new_row = {'TIMESTAMP': timestamp, 'NODE': node, 'EXPECTED': 1}
            self.data = pd.concat([self.data, pd.DataFrame([new_row])], ignore_index=True)
        self.data.to_csv('expected_congestion.csv', index=False)


    def temporal_moving_average(self, data, window):
        return data.rolling(window=window).mean()

    def predict_congestion_mavg(self, t, node, line):
        CI = self.data[self.data['NODE'] == node]

        # If no data is available for the node, return 0
        if len(CI) == 0:
            return 0

        # Apply temporal moving average if technique is specified
        window = 5 # Default to window=1 if not provided
        # Compute rolling mean
        CI_mod = CI.copy()  # Ensure it's a separate dataframe
        CI_mod.loc[:, 'CONGESTION INDEX MA'] = CI['CONGESTION INDEX'].rolling(window=window).mean()
        print('Computing congestion')
        return CI_mod['CONGESTION INDEX MA'].iloc[-1]

        # Default return if no technique applies
        value = CI['CONGESTION INDEX'].iloc[-1]
        if np.isnan(value):
            value = 0
        return value

    def predict_congestion(self, t, node, line):
        t = self.align_to_next_departure(t, node, line)
        print('PREDICT CONGESTION for ', t, node, line)
        CI = self.data[self.data['NODE'] == node].copy(deep=True)
        print(CI.iloc[:, :])
        if len(CI) == 0:
            print('NO CONGESTION INFO for node', node)
            return 0
        else:
            #CI['time_diff'] = [(x - t).total_seconds() for x in CI.TIMESTAMP]
            #CI = CI[CI['time_diff'] >= 0]
            #CI = CI.sort_values(by=['time_diff', 'EXPECTED']).reset_index(drop=True, inplace=False)
            CI = self.data[self.data['TIMESTAMP'] >= t].reset_index(drop=True)
            if len(CI) == 0:
                print('NO CONGESTION INFO for time', t, node)
                return 0
            else:
                print('CONGESTION INFO for time', t, node, CI.loc[0, 'EXPECTED'])
                return CI.loc[0, 'EXPECTED']

    def clear_data(self):
        """
        Clears all congestion data.
        """
        self.data.clear()

    def write_congestion(self, path):
        self.data.to_csv(f'{path}{os.sep}congestion_history.csv')
