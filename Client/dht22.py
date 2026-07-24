import time

import dht22_takemoto as dht22


dht22_instance = dht22.DHT22(gpio=26)

DIAGNOSTIC_SECONDS = 120
DIAGNOSTIC_INTERVAL_SEC = 5


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


def get_dht_data_with_status():
    try:
        temp, humid = _read_once()
        return temp, humid, "ok", None
    except Exception as e:
        error_code = _short_error(e)
        raise DHT22ReadError(
            f"DHT22 sensor read failed: {error_code}",
            error_code=error_code,
        ) from e


def get_dht_data():
    temp, humid, _, _ = get_dht_data_with_status()
    return temp, humid


def close():
    dht22_instance.close()


if __name__ == "__main__":
    end_at = time.time() + DIAGNOSTIC_SECONDS
    counts = {"ok": 0, "failed": 0}
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
