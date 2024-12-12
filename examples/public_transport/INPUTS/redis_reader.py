import redis
import pandas as pd
from datetime import datetime, timedelta
import time


# Connect to Redis (adjust host and port)
redis_client = redis.StrictRedis(host='137.121.163.115', port=6379, decode_responses=True)


## Reading from Redis

def get_current_time_bin(tcurrent, bin_minutes=10):

    # Calculate the start of the bin
    bin_start = tcurrent - timedelta(minutes=tcurrent.minute % bin_minutes, seconds=tcurrent.second, microseconds=tcurrent.microsecond)

    # Return the bin as a formatted string
    return bin_start.strftime("%Y-%m-%d %H:%M:%S")

#now = datetime.now()   # Replace with tcurrent
#time_bin = get_current_time_bin(now, bin_minutes=10)

user = "30303030303036330018B7C27651636EED8FA067D7392487B994DB5599A1E3D2"
target = "TRAM_T4_LABORELLE-10:11"

target2 = "TRAM_T4_LABORELLE-10:10"

# Retrieve the BI value for the given time_bin
BI_value2 = redis_client.hget(user, target)

# Output the result
if BI_value2 is not None:
    print(f"The BI value for user '{user}', target '{target}' is: {BI_value2}")
else:
    print(f"No BI value found for user '{user}', target '{target}'.")

if BI_value2 is None:
    BI_value2 = 0

print(BI_value2)

start_time = time.time()
# Retrieve the BI value for the given time_bin
BI_value = redis_client.hget(user, target2)
end_time = time.time()
print(f"Total execution time: {end_time - start_time:.6f} seconds")

# Output the result
if BI_value is not None:
    print(f"The BI value for user '{user}', target '{target2}' is: {BI_value}")
else:
    print(f"No BI value found for user '{user}', target '{target2}'.")

if BI_value is None:
    BI_value = 0

print(BI_value)