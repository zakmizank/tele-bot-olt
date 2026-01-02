import time
import requests, base64, logging, re
from typing import Dict, Any
import pymysql as mysql
import hashlib


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ONUCollector")

# ---------------- DB CONFIG ----------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "",
    "password": "",
    "database": "db_mng_olt",
    "autocommit": True
}

# ---------------- HELPER ----------------
def validate_ip(ip: str) -> bool:
    return bool(re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip)) and all(0 <= int(p) <= 255 for p in ip.split('.'))

def safe_json(resp: requests.Response) -> Dict[str, Any]:
    try:
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "text": resp.text[:200]}
        return resp.json()
    except Exception as e:
        return {"error": str(e), "raw": resp.text[:200]}
def safe_float(val):
    try:
        if val in [None, "", "N/A", "null", "-inf", "inf", "+inf"]:
            return None
        f = float(val)
        if f == float("inf") or f == float("-inf"):
            return None
        return f
    except Exception:
        return None


# ---------------- OLT ----------------
def olt_login(olt_ip: str, username: str, password: str) -> Dict[str, Any]:
    # password di-encode base64
    password_b64 = base64.b64encode(password.encode()).decode()

    # key = md5(username:password)
    raw_key = f"{username}:{password}"
    key = hashlib.md5(raw_key.encode()).hexdigest()

    login_url = f"http://{olt_ip}/userlogin?form=login"
    payload = {
        "method": "set",
        "param": {
            "name": username,
            "key": key,
            "value": password_b64,
            "captcha_v": "",
            "captcha_f": ""
        }
    }

    resp = requests.post(login_url, json=payload, timeout=10)
    data = safe_json(resp)

    if data.get("code") != 1:
        raise Exception(f"Login failed: {data}")
    x_token = resp.headers.get("X-Token")
    if not x_token:
        raise Exception("No X-Token in login response")

    return {"headers": {"X-Token": x_token}, "login_data": data}


def olt_get_data(olt_ip: str, username: str, password: str):
    auth_data = olt_login(olt_ip, username, password)
    headers = auth_data["headers"]

    # --- system hostname ---
    try:
        system_url = f"http://{olt_ip}/system?form=hostname"
        system_resp = requests.get(system_url, headers=headers, timeout=10)
        hostname = safe_json(system_resp).get("data", {}).get("hostname", olt_ip)
    except Exception:
        hostname = olt_ip

    # --- board info + trigger onu_allow_list ---
    try:
        board_url = f"http://{olt_ip}/board?info=pon"
        board_resp = requests.get(board_url, headers=headers, timeout=10)
        board_data = safe_json(board_resp)
        if "data" in board_data:
            for port in board_data["data"]:
                try:
                    ts = int(time.time() * 1000)
                    allow_url = f"http://{olt_ip}/onu_allow_list?t={ts}"
                    requests.get(allow_url, headers=headers, timeout=5)
                except:
                    continue
    except Exception as e:
        logger.warning(f"Failed to get board info from {olt_ip}: {e}")

    # --- fetch onu table ---
    onu_url = f"http://{olt_ip}/onutable"
    onu_resp = requests.get(onu_url, headers=headers, timeout=15)
    onu_data = safe_json(onu_resp)

    return hostname, onu_data.get("data", [])


# ---------------- MAIN ----------------
def main():
    conn = mysql.connect(**DB_CONFIG)
    cur = conn.cursor(mysql.cursors.DictCursor)

    # Ambil daftar OLT dari tabel olt
    cur.execute("SELECT id, ip, username, password FROM olt ORDER BY id ASC")
    olts = cur.fetchall()

    for olt in olts:
        olt_id, ip, user, pwd = olt["id"], olt["ip"], olt["username"], olt["password"]
        logger.info(f"Collecting ONU data from {ip} ...")
        try:
            olt_hostname, onus = olt_get_data(ip, user, pwd)
            logger.info(f"OLT {olt_hostname} has {len(onus)} ONUs")

            for onu in onus:
                cur.execute("""
                    INSERT INTO onu_log (
                        olt_id, olt_ip, olt_hostname,
                        onu_id, onu_name, macaddr, port_id,
                        status, receive_power, rtt,
                        auth_state, vendor,
                        last_down_reason, last_down_time, register_time,
                        created_at
                    ) VALUES (
                        %s,%s,%s,
                        %s,%s,%s,%s,
                        %s,%s,%s,
                        %s,%s,
                        %s,%s,%s,
                        NOW()
                    )
                """, (
                    olt_id, ip, olt_hostname,
                    onu.get("onu_id"), onu.get("onu_name"), onu.get("macaddr"), onu.get("port_id"),
                    onu.get("status"), safe_float(onu.get("receive_power")), onu.get("rtt"),
                    onu.get("auth_state"), onu.get("vendor"),
                    onu.get("last_down_reason"), onu.get("last_down_time"), onu.get("register_time")
                ))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to collect from {ip}: {e}")


    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
