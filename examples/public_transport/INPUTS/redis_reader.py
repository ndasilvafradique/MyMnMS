import redis
import pandas as pd
from datetime import datetime, timedelta

# Connect to Redis (adjust host and port)
redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)


## Reading from Redis

def get_current_time_bin(tcurrent, bin_minutes=10):

    # Calculate the start of the bin
    bin_start = tcurrent - timedelta(minutes=tcurrent.minute % bin_minutes, seconds=tcurrent.second, microseconds=tcurrent.microsecond)

    # Return the bin as a formatted string
    return bin_start.strftime("%Y-%m-%d %H:%M:%S")

#now = datetime.now()   # Replace with tcurrent
#time_bin = get_current_time_bin(now, bin_minutes=10)

user = "303030303030363300045568D4FC2F1C99B5AAE0326B11C7098451A5C84B29C7"
target = "VEB::68::10797::Cite Tase"
time_bin = "1900-01-01 09:00:00"

# Construct the Redis hash key
hash_key = f"{user}::{target}"

# Retrieve the BI value for the given time_bin
BI_value = redis_client.hget(hash_key, time_bin)

# Output the result
if BI_value is not None:
    print(f"The BI value for user '{user}', target '{target}', and time '{time_bin}' is: {BI_value}")
else:
    print(f"No BI value found for user '{user}', target '{target}', and time '{time_bin}'.")

if BI_value is None:
    BI_value = 0

print(BI_value)