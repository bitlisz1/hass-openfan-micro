import requests


def get_fan_status(host):
    url = f"http://{host}/api/v0/fan/status"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise RuntimeError("Fan returned error status.")

    return {
        "speed_pct": data["pwm_percent"],
        "speed_rpm": data["rpm"],
    }


def set_fan_speed(host, speed_pct):
    url = f"http://{host}/api/v0/fan/0/set"
    params = {"value": int(speed_pct)}
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()


def test_connection(host):
    """Check if the OpenFAN Micro device is reachable and responding."""
    try:
        resp = requests.get(f"http://{host}/api/v0/fan/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            return False
        return True
    except (requests.RequestException, ValueError):
        return False
