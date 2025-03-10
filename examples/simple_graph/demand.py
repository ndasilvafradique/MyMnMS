import json
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.stats import norm


def generate_morning_peak_departures(num_users, start_time='06:00:00', end_time="07:45:00", peak_hour=7.5, peak_std=1,
                                     output_file="morning_peak_demand.json"):
    """
    Generates departure data simulating a morning peak using a normal distribution.

    Args:
        num_users (int): The number of users.
        peak_hour (int): The hour of the peak (e.g., 8 for 8 AM).
        peak_std (float): The standard deviation of the peak (controls the width).
        output_file (str): The name of the output JSON file.
    """

    data = pd.DataFrame(columns=['ID', 'DEPARTURE', 'ORIGIN', 'DESTINATION', 'MOBILITY SERVICES'])
    start_hour, start_minute, start_second = map(int, start_time.split(':'))
    start_timedelta = timedelta(hours=start_hour, minutes=start_minute, seconds=start_second)

    end_hour, end_minute, end_second = map(int, end_time.split(':'))
    end_total_minutes = (end_hour - start_hour) * 60 + end_minute

    for user_id in range(1, num_users + 1):
        # Generate a random departure time around the peak using a normal distribution
        departure_hour = np.random.normal(loc=peak_hour, scale=peak_std)

        # Ensure departure hour is within a reasonable range (start to end time)
        departure_hour = max(start_hour, min(end_hour + (end_minute / 60), departure_hour))

        # Convert departure hour to minutes relative to the start time
        departure_minutes = int((departure_hour - start_hour) * 60)

        # Ensure departure minutes are within the end time.
        departure_minutes = min(departure_minutes, end_total_minutes)

        # Convert minutes to HH:MM:SS format relative to start time
        departure_time = start_timedelta + timedelta(minutes=departure_minutes)
        departure_time_str = str(departure_time)

        user_id_mod = ''
        if user_id % 2 == 0:
            user_id_mod = f'U_M{user_id}'
        else:
            user_id_mod = f'U_B{user_id}'

        new_row = pd.DataFrame({'ID': [user_id_mod], 'DEPARTURE': [departure_time_str],
                                'ORIGIN': ['0 0'], 'DESTINATION': ['3000 0'], 'MOBILITY SERVICES': ['METRO TRAM BUS']})
        data = pd.concat([data, new_row], ignore_index=True)

    print(data.head())
    print(data.info())
    data.sort_values(by='DEPARTURE', inplace=True)
    data.to_csv(output_file, index=False, sep=';')
    print(f"Morning peak departure data saved to {output_file}")
    return data


# Example usage:
num_users = 2000
peak_hour = 7
peak_std = 0.7  # Adjust for wider/narrower peak
start_time = '06:30:00'
end_time = "07:30:00"
generate_morning_peak_departures(num_users, start_time, end_time, peak_hour, peak_std,
                                 "morning_peak_demand.csv")






