import redis
import pandas as pd
from datetime import datetime, timedelta

# Connect to Redis (adjust host and port)
redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

df = pd.read_csv('human_behavior_mod.csv')
'''
# Iterate over rows to populate Redis
for _, row in df.iterrows():
    # A Redis hash key for each unique combination of NUMERO_SERIE_TITRE_TRANSPORT and target
    hash_key = f"{row['NUMERO_SERIE_TITRE_TRANSPORT']}::{row['target']}"

    # time_bin as the field and BI as the value
    time_bin = row['time_bin']
    BI = row['BI']

    # Add the time_bin -> BI pair to the hash
    redis_client.hset(hash_key, time_bin, BI)
'''
for _, row in df.iterrows():
    # A Redis hash key for each NUMERO_SERIE_TITRE_TRANSPORT
    hash_key = row['NUMERO_SERIE_TITRE_TRANSPORT']

    # couple target - time_bin as the field and BI as the value
    target = row['target']
    time_bin = row['time_bin']
    # Extract hour and minute from time_bin
    hour_minute = time_bin.split(' ')[1][:5]  # Extract HH:mm
    BI = row['BI']

    # Add the time_bin -> BI pair to the hash
    redis_client.hset(hash_key, f"{target}-{hour_minute}", BI)

