import time
import hashlib
from flask import Blueprint, jsonify, request
import requests, base64, logging
from typing import Dict, Any
import re

onu_bp = Blueprint("onu", __name__)
logger = logging.getLogger(__name__)


def validate_ip(ip: str) -> bool:
    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
    if not re.match(ip_pattern, ip):
        return False
    
    parts = ip.split('.')
    for part in parts:
        if not 0 <= int(part) <= 255:
            return False
    return True

def safe_json(resp: requests.Response) -> Dict[str, Any]:
    """Safely parse JSON response with error handling"""
    try:
        if resp.status_code != 200:
            return {
                "error": f"HTTP Error {resp.status_code}",
                "status_code": resp.status_code,
                "text": resp.text[:200]
            }
        return resp.json()
    except ValueError as e:
        return {"error": f"JSON Parse Error: {str(e)}", "raw": resp.text[:200], "status_code": resp.status_code}
    except Exception as e:
        return {"error": f"Unexpected Error: {str(e)}", "status_code": resp.status_code}

class OLTAuthError(Exception):
    pass

class OLTConnectionError(Exception):
    pass

def olt_login(olt_ip: str, username: str, password: str) -> Dict[str, Any]:
    """Handle OLT login and return headers"""
    try:

        password_b64 = base64.b64encode(password.encode()).decode()


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
        login_data = safe_json(resp)

        if login_data.get("code") != 1:
            raise OLTAuthError(f"Login failed: {login_data.get('message', 'Unknown error')}")

        x_token = resp.headers.get("X-Token")
        if not x_token:
            raise OLTAuthError("No X-Token received in login response")

        return {
            "x_token": x_token,
            "headers": {"X-Token": x_token},
            "login_data": login_data
        }

    except requests.exceptions.Timeout:
        raise OLTConnectionError("Login timeout - OLT not responding")
    except requests.exceptions.ConnectionError:
        raise OLTConnectionError("Connection failed - check OLT IP address")
    except requests.exceptions.RequestException as e:
        raise OLTConnectionError(f"Network error: {str(e)}")

def olt_get_data(olt_ip: str, username: str, password: str) -> Dict[str, Any]:
    """Main function to retrieve OLT data"""
    try:

        if not validate_ip(olt_ip):
            return {"error": "Invalid IP address format"}
        

        auth_data = olt_login(olt_ip, username, password)
        headers = auth_data["headers"]
        
        result = {
            "login": auth_data["login_data"],
            "x_token": auth_data["x_token"],
            "system": {},
            "board": {},
            "onus": [],
            "total_onus": 0,
            "success": True
        }


        try:
            system_url = f"http://{olt_ip}/system?form=hostname"
            system_resp = requests.get(system_url, headers=headers, timeout=10)
            result["system"] = safe_json(system_resp)
        except Exception as e:
            logger.warning(f"Failed to get system info: {str(e)}")
            result["system"] = {"error": str(e)}


        try:
            board_url = f"http://{olt_ip}/board?info=pon"
            board_resp = requests.get(board_url, headers=headers, timeout=10)
            board_data = safe_json(board_resp)
            result["board"] = board_data
            

            if "data" in board_data:
                pon_ports = [p["port_id"] for p in board_data.get("data", [])]
                for pid in pon_ports:
                    try:
                        ts = int(time.time() * 1000)
                        allow_url = f"http://{olt_ip}/onu_allow_list?t={ts}"
                        requests.get(allow_url, headers=headers, timeout=5)
                    except Exception:
                        continue  # Skip if one port fails
        except Exception as e:
            logger.warning(f"Failed to get board info: {str(e)}")
            result["board"] = {"error": str(e)}

        # Get ONU data
        try:
            onu_url = f"http://{olt_ip}/onutable"
            onu_resp = requests.get(onu_url, headers=headers, timeout=15)
            onu_data = safe_json(onu_resp)
            
            if "data" in onu_data:
                result["onus"] = onu_data["data"]
                result["total_onus"] = len(onu_data["data"])
            else:
                result["onus"] = onu_data
        except Exception as e:
            logger.error(f"Failed to get ONU data: {str(e)}")
            result["onus"] = {"error": str(e)}

        return result

    except OLTAuthError as e:
        return {"error": str(e), "success": False}
    except OLTConnectionError as e:
        return {"error": str(e), "success": False}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "success": False}

@onu_bp.route("/", methods=["GET"])
def get_onu_list():
    """API endpoint to get ONU list from OLT"""
    olt_ip = request.args.get("ip")
    username = request.args.get("username", "root")
    password = request.args.get("password", "")
    

    logger.info(f"Request received for OLT: {olt_ip}, user: {username}")

    if not olt_ip or not password:
        return jsonify({
            "error": "Parameter ip dan password wajib",
            "success": False
        }), 400

    result = olt_get_data(olt_ip, username, password)
    

    if result.get("success"):
        logger.info(f"Successfully retrieved {result.get('total_onus', 0)} ONUs from {olt_ip}")
    else:
        logger.error(f"Failed to retrieve data from {olt_ip}: {result.get('error')}")
    
    return jsonify(result)

@onu_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "ONU Data Collector",
        "timestamp": time.time()
    })