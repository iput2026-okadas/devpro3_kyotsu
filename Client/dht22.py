import dht22_takemoto as dht22
import time

dht22_instance = dht22.DHT22(gpio=26)

WAIT_INTERVAL = 2
WAIT_INTERVAL_RETRY = 5

def get_dht_data():

    try:
        temp, humid, _ = dht22_instance.read()
    
    except dht22.DHT22CRCError:
        time.sleep(WAIT_INTERVAL_RETRY)
        raise(dht22.DHT22CRCError)

    except dht22.DHT22MissingDataError:
        time.sleep(WAIT_INTERVAL_RETRY)
        raise dht22.DHT22MissingDataError

    return float(temp), float(humid)
