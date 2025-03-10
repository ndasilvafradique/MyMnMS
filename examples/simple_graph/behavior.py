import pickle

import numpy as np
import pandas as pd


# # Parametri
# time_intervals = 288  # 24 ore divise in fasce da 5 minuti
# stations = ["BUS_S3", "BUS_S1", "METRO_SO", "TRAM_S3", "BUS_SO"]  # Lista delle stazioni
# user_id = "U0"  # ID utente fisso per esempio


def generate_preference_curve(intervals, peak_hour=7, spread=3, noise=0.1):
    """
    Genera una curva di preferenza con un picco attorno a un'ora specificata.
    """
    hours = np.linspace(0, 24, intervals)
    peak = np.exp(-0.5 * ((hours - peak_hour) / spread) ** 2)  # Distribuzione gaussiana
    peak = (peak - peak.min()) / (peak.max() - peak.min())  # Normalizzazione [0,1]
    peak += np.random.normal(0, noise, size=intervals)  # Aggiunta di rumore
    return np.clip(peak, 0, 1)


def create_behavior(stations, time_intervals, n_users=100):
    # Creazione della lista delle preferenze
    data = []
    for u in range(n_users):
        for station in stations:
            peak_hour = np.random.randint(6, 21)  # Ogni stazione ha un picco casuale
            spread = np.random.uniform(2, 5)  # Diversa ampiezza del picco
            preferences = generate_preference_curve(time_intervals, peak_hour, spread)

            for i, time in enumerate(pd.date_range("00:00", periods=time_intervals, freq="5min").time):
                data.append([f'U{u}', time.strftime('%H:%M:%S'), station, round(preferences[i], 4)])

    # Creazione di un DataFrame
    df = pd.DataFrame(data, columns=["ID", "TIME", "STATION", "BI"])
    df.to_csv('behavior.csv', index=False, sep=';')


'''def create_behavior(filename, tstart, tend, stations, n_users=1):
    # Ensure tstart and tend are datetime.time objects
    if isinstance(tstart, str):
        tstart = datetime.datetime.strptime(tstart, "%H:%M:%S").time()
    if isinstance(tend, str):
        tend = datetime.datetime.strptime(tend, "%H:%M:%S").time()

    # Convert time to datetime for iteration
    today = datetime.datetime.today()  # Get today's date
    tstart_dt = datetime.datetime.combine(today, tstart)
    tend_dt = datetime.datetime.combine(today, tend)

    with open(filename, 'w') as f:
        f.write('ID;TIME;STATION;BI\n')
        for i in range(n_users):
            current_time = tstart_dt
            while current_time < tend_dt:
                for s in stations:
                    BI = random.random()
                    time_str = current_time.strftime("%H:%M:%S")
                    f.write(f'U{i};{time_str};{s};{BI:.4f}\n')
                current_time += datetime.timedelta(seconds=60)  # Increment by 1 minute
'''


def read_behavior(input_file, total_per_t=False):
    # Load the data
    df = pd.read_csv(input_file, delimiter=",")  # Change to "," if it's comma-separated

    # Melt the dataframe to long format
    df_melted = df.melt(id_vars=["ID", "TIME"], var_name="STATION", value_name="VALIDATIONS")

    # Save as a semicolon-separated CSV
    print(df_melted)

    if total_per_t:
        total_visits = df_melted.groupby(by=["ID", "TIME"])["VALIDATIONS"].sum()
        df_melted = df_melted.merge(total_visits, on=["ID", "TIME"], suffixes=("", "_per_time"))

        # Divide VALIDATIONS by the total_visits for each ID-TIME
        df_melted["BI"] = df_melted["VALIDATIONS"] / df_melted["VALIDATIONS_per_time"]
        output_file = input_file.split('.')[0] + '_per_time.csv'
        df_melted.to_csv(output_file, sep=";", index=False)
    else:
        total_visits = df_melted.groupby(by=["ID"])["VALIDATIONS"].sum()
        df_melted = df_melted.merge(total_visits, on="ID", suffixes=("", "_total"))

        # Divide VALIDATIONS by the total_visits for each ID
        df_melted["BI"] = df_melted["VALIDATIONS"] / df_melted["VALIDATIONS_total"]
        output_file = input_file.split('.')[0] + '_total_visits.csv'
        df_melted.to_csv(output_file, sep=";", index=False)

    print(f"Transformed CSV saved as {output_file}")


def create_test_profile(num_users, start, end, freq='5min'):
    # Define user parameters
    time_intervals = pd.date_range(start, end, freq=freq).time  # 5-minute intervals

    # Station columns
    columns = ["ID", "TIME"]
    with open('stations.pkl', 'rb') as f:
        stations = pickle.load(f)
    columns += list(stations)
    print(columns)

    # Storage for data
    data = []

    for user_id in range(num_users):
        for time in time_intervals:
            if user_id % 2 == 0:  # Even users prefer metro
                row = [ f"U_M{user_id}", time]
                for station in stations:
                    if 'METRO' in station:
                        row.append(1)
                    elif 'TRAM' in station:
                        row.append(0.5)
                    elif 'BUS' in station:
                        row.append(0)

            else:  # Odd users prefer buses
                row = [f"U_B{user_id}", time]
                for station in stations:
                    if 'METRO' in station:
                        row.append(0)
                    elif 'TRAM' in station:
                        row.append(0.5)
                    elif 'BUS' in station:
                        row.append(1)
            data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data, columns=columns)

    # Save to CSV
    df.to_csv("user_travel_profiles.csv", index=False)

    # Print sample data
    print(df.head(20))


if __name__ == '__main__':
    create_test_profile(2000,  start='5:30:00', end='08:00:00')
    read_behavior('user_travel_profiles.csv', True)
    read_behavior('user_travel_profiles.csv', False)
