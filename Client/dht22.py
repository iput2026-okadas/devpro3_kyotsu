import time

import dht22_takemoto as dht22


dht22_instance = dht22.DHT22(gpio=26)

READ_RETRY_COUNT = 3
RETRY_DELAY_SEC = 2.5
LAST_VALID_MAX_AGE_SEC = 60
DIAGNOSTIC_SECONDS = 120
DIAGNOSTIC_INTERVAL_SEC = 5

_last_valid_data = None
_last_valid_at = None


class DHT22ReadError(Exception):
    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code


def _short_error(error):
    if isinstance(error, dht22.DHT22CRCError):
        return "CRC"
    if isinstance(error, dht22.DHT22MissingDataError):
        return "missing_data"
    return error.__class__.__name__


def _read_once():
    temp, humid, _ = dht22_instance.read()
    return float(temp), float(humid)


def _remember_valid(temp, humid):
    global _last_valid_data, _last_valid_at
    _last_valid_data = (temp, humid)
    _last_valid_at = time.time()


def _last_valid_is_fresh():
    if _last_valid_data is None or _last_valid_at is None:
        return False
    return time.time() - _last_valid_at <= LAST_VALID_MAX_AGE_SEC


def get_dht_data_with_status():
    last_error = None

    for attempt in range(READ_RETRY_COUNT):
        try:
            temp, humid = _read_once()
            _remember_valid(temp, humid)
            return temp, humid, "ok", None
        except (dht22.DHT22CRCError, dht22.DHT22MissingDataError) as e:
            last_error = e
        except Exception as e:
            last_error = e

        if attempt < READ_RETRY_COUNT - 1:
            time.sleep(RETRY_DELAY_SEC)

    error_code = _short_error(last_error) if last_error is not None else "unknown"

    if _last_valid_is_fresh():
        temp, humid = _last_valid_data
        return temp, humid, "stale", error_code

    raise DHT22ReadError(
        f"DHT22 sensor read failed after {READ_RETRY_COUNT} attempts: {error_code}",
        error_code=error_code,
    )


def get_dht_data():
    temp, humid, _, _ = get_dht_data_with_status()
    return temp, humid


def close():
    dht22_instance.close()


if __name__ == "__main__":
    end_at = time.time() + DIAGNOSTIC_SECONDS
    counts = {"ok": 0, "stale": 0, "failed": 0}
    errors = {}

    try:
        while time.time() < end_at:
            try:
                temp, humid, status, error = get_dht_data_with_status()
                counts[status] += 1
                if error is not None:
                    errors[error] = errors.get(error, 0) + 1
                print(
                    f"DHT22 {status}: temp={temp:.1f} C, humid={humid:.1f} %, error={error}"
                )
            except DHT22ReadError as e:
                counts["failed"] += 1
                error = e.error_code or "unknown"
                errors[error] = errors.get(error, 0) + 1
                print(f"DHT22 failed: {error}")

            time.sleep(DIAGNOSTIC_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("End of DHT22 diagnostic.")
    finally:
        print(f"DHT22 summary: {counts}, errors={errors}")
        close()
