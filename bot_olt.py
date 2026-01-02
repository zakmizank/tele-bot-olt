#!/usr/bin/env python3
import asyncio
import subprocess
import re
import time
import pymysql
from datetime import datetime
from collections import defaultdict
from telegram import Bot
from telegram.error import TelegramError
import shlex


DB_CONFIG = {
    'host': 'localhost',
    'user': '',  
    'password': 'mngpass',  
    'database': 'db_mng_olt', 
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

dying_gasp_mac = defaultdict(float)
mati_lampu_mac = defaultdict(float) 

def get_last_rx(mac):

    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT receive_power 
                FROM onu_log 
                WHERE macaddr = %s 
                ORDER BY created_at DESC
                LIMIT 50
            """, (mac,))
            results = cursor.fetchall()

        if not results:
            return "N/A", "database"

        for row in results:
            if row["receive_power"] is not None:
                return f"{row['receive_power']} dBm", "database"

        return "N/A", "database"

    except Exception as e:
        print(f"DB RX error: {e}")
        return "N/A", "database"
    finally:
        if conn:
            conn.close()

def get_rx_snmp_only(olt_ip, pon, slot):
    community_read, _ = get_snmp_community(olt_ip)
    if not community_read:
        return None, None

    onu_id = calculate_onu_id(pon, slot)
    rx_oid = f".1.3.6.1.4.1.50224.3.3.3.1.4.{onu_id}.0.0"

    try:
        rx_cmd = f"snmpget -v2c -c {community_read} {olt_ip} {rx_oid}"
        rx_out = subprocess.check_output(
            shlex.split(rx_cmd),
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode()

        match = re.search(r'INTEGER:\s*(-?\d+)', rx_out)
        if not match:
            return None, None

        rx_dbm = f"{int(match.group(1)) / 100:.2f} dBm"
        return rx_dbm, "olt"

    except Exception as e:
        print(f"SNMP RX error: {e}")
        return None, None

def get_rx_with_source(data_log, category):

    if category == 'up':
        rx, source = get_rx_snmp_only(
            data_log['olt_ip'],
            data_log['pon'],
            data_log['slot']
        )
        if rx:
            return rx, source


    return get_last_rx(data_log['mac'])

def calculate_onu_id(pon, slot):
    """Hitung ID ONU berdasarkan rumus HSGQ"""
    return 16777472 + (pon - 1) * 256 + slot

def get_onu_name_from_db(mac):
    """Ambil nama ONU terakhir dari onu_log"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT onu_name
                FROM onu_log
                WHERE macaddr = %s
                  AND onu_name IS NOT NULL
                  AND onu_name != ''
                ORDER BY created_at DESC
                LIMIT 1
            """, (mac,))
            row = cursor.fetchone()
        conn.close()

        return row['onu_name'] if row else "-"

    except Exception as e:
        print(f"DB ONU NAME error: {e}")
        return "-"



def get_snmp_community(olt_ip):
    """
    Ambil community SNMP dari tabel olt
    kolom: ip, community_read, community_write
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT community_read, community_write
                FROM olt
                WHERE ip = %s
                LIMIT 1
            """, (olt_ip,))
            row = cursor.fetchone()
        conn.close()

        if not row:
            return None, None

        return row['community_read'], row['community_write']

    except Exception as e:
        print(f"ERROR ambil community SNMP: {e}")
        return None, None

def insert_olt_log(raw_log, log_time, hostname, mac_address):
    """Insert data ke tabel olt_logs"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO olt_logs (raw_log, log_time, hostname, mac_address)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (raw_log, log_time, hostname, mac_address))
        conn.commit()
        conn.close()
        print(f"SUCCESS: Data inserted to olt_logs - MAC: {mac_address}")
    except pymysql.Error as err:
        print(f"ERROR: Gagal insert ke olt_logs: {err}")
    except Exception as e:
        print(f"ERROR: Unexpected error insert olt_logs: {e}")

def get_bot_token():
    """Ambil token bot dari database"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT token FROM telegram_bot LIMIT 1")
            result = cursor.fetchone()
        conn.close()
        
        if result:
            return result['token']
        else:
            raise Exception("Token bot tidak ditemukan di database")
    except pymysql.Error as err:
        print(f"Database error: {err}")
        raise Exception(f"Gagal mengambil token dari database: {err}")

def get_chat_ids():
    """Ambil chat IDs dari database"""
    chat_ids = {
        "mati": [],
        "los": [],
        "up": []
    }
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT kategori, chat_id FROM telegram_chat")
            results = cursor.fetchall()
        conn.close()
        
        for row in results:
            kategori = row['kategori']
            chat_id = row['chat_id']
            if kategori in chat_ids:
                chat_ids[kategori].append(chat_id)
        
        return chat_ids
    except pymysql.Error as err:
        print(f"Database error: {err}")

        return chat_ids

def get_server_time():
    """Dapatkan waktu server yang sudah diformat"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def parse_log_line(line):
    """Parse log line dan ekstrak informasi"""
    print(f"DEBUG: Processing line: {line.strip()}")
    

    pattern = (
        r'^(\w+\s+\d+\s+\d+:\d+:\d+)\s+'  
        r'(\S+)\s+'                        
        r'([^:]+):\s+'                    
        r'\[[^\]]+\]\s+'                  
        r'Info:\s+'
        r'(ONU\s+\d+/\d+(?:\s+Port\s+\d+)?\s+[0-9a-f:]+)\s+'  
        r'(.*)$'                           
    )
    match = re.match(pattern, line)
    
    if not match:
        print("DEBUG: No regex match with main pattern")
        return None
    
    waktu, gateway_or_ip, olt_name, onu_info, status = match.groups()
    print(f"DEBUG: Parsed - waktu={waktu}, gateway_or_ip={gateway_or_ip}, olt_name={olt_name}, onu_info={onu_info}, status={status}")
    

    mac_match = re.search(r'([0-9a-f:]{17})', onu_info)
    mac = mac_match.group(1) if mac_match else None
    pon_slot_match = re.search(r'ONU\s+(\d+)/(\d+)', onu_info)
    pon = int(pon_slot_match.group(1)) if pon_slot_match else None
    slot = int(pon_slot_match.group(2)) if pon_slot_match else None

    return {
        'waktu_server': get_server_time(),
        'waktu_olt': waktu.strip(),
        'olt': f"{gateway_or_ip} {olt_name}".strip(),
        'olt_ip': gateway_or_ip,
        'onu_info': onu_info.strip(),
        'status': status.strip(),
        'mac': mac,
        'pon': pon,
        'slot': slot,
        'raw_log': line.strip()
    }
def kategori_log(data_log):
    if not data_log or 'mac' not in data_log or not data_log['mac']:
        return None

    status = data_log['status'].lower()
    mac = data_log['mac']
    current_time = time.time()


    if 'dying gasp' in status:

        dying_gasp_mac[mac] = current_time
        mati_lampu_mac[mac] = current_time
        return 'mati'


    if mac in mati_lampu_mac:
        time_since_mati_lampu = current_time - mati_lampu_mac[mac]
        

        if time_since_mati_lampu < 10:

            if 'link up' in status:
                if mac in mati_lampu_mac:
                    del mati_lampu_mac[mac]
                if mac in dying_gasp_mac:
                    del dying_gasp_mac[mac]
                return 'up'
            else:
                print(f"DEBUG: Abaikan pesan untuk MAC {mac} (periode 10 detik setelah mati lampu): {status}")
                return None
        
        else:
            if mac in mati_lampu_mac:
                del mati_lampu_mac[mac]
            if mac in dying_gasp_mac:
                del dying_gasp_mac[mac]


    if 'laser out' in status:
        return 'los'

    if 'only ctc lost' in status:
        return 'los'


    if 'link up' in status:
        return 'up'


    if 'manual reboot' in status:
        return 'mati'

    return None



def format_message(data_log, category):
    rx_value, rx_source = get_rx_with_source(data_log, category)
    onu_name = get_onu_name_from_db(data_log['mac'])

    status_map = {
        'mati': '⚠️ MATI LAMPU',
        'los': '🚨 ONU LOS',
        'up': '✅ ONU UP'
    }

    return f"""{status_map[category]}

🕒 Waktu Server: {data_log['waktu_server']}

⏰ Waktu OLT: {data_log['waktu_olt']}

💻 OLT: {data_log['olt']}

📛 Nama ONU: {onu_name}

📡 ONU: {data_log['onu_info'].replace('ONU ', '')}

📶 RX Terakhir: {rx_value} ({rx_source})

📝 Info: {data_log['status']}
"""
    return message


async def send_to_telegram(message, category, bot, chat_ids, data_log):
    """Kirim pesan ke grup Telegram dan insert ke database"""
    if category not in chat_ids or not chat_ids[category]:
        print(f"WARNING: Tidak ada chat ID untuk kategori {category}")
        return
    

    insert_olt_log(
        raw_log=data_log['raw_log'],
        log_time=data_log['waktu_server'],
        hostname=data_log['olt'],
        mac_address=data_log['mac']
    )
    
    for chat_id in chat_ids[category]:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            print(f"SUCCESS: Pesan terkirim ke {category}: {chat_id}")
        except TelegramError as e:
            print(f"ERROR: Gagal mengirim ke {category}: {e}")

async def monitor_log():
    """Monitor log file dan proses log baru"""
    print("Memulai monitoring log OLT...")
    

    try:
        BOT_TOKEN = get_bot_token()
        CHAT_IDS = get_chat_ids()
        bot = Bot(token=BOT_TOKEN)
        
        print("Berhasil mengambil konfigurasi dari database")
        print(f"Token: {BOT_TOKEN}")
        print(f"Chat IDs: {CHAT_IDS}")
    except Exception as e:
        print(f"ERROR: Gagal mengambil konfigurasi dari database: {e}")
        return
    
    print(f"Memonitor file: /var/log/olt.log")
    

    process = subprocess.Popen(
        ['tail', '-n0', '-F', '/var/log/olt.log'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    print("Menunggu log baru...")
    
    while True:
        line = process.stdout.readline()
        if not line:
            await asyncio.sleep(0.1)
            continue
        
        print(f"LOG BARU: {line.strip()}")
        

        data_log = parse_log_line(line)
        if not data_log:
            print("DEBUG: Gagal parse log, skip")
            continue
            
        if not data_log.get('mac'):
            print("DEBUG: Tidak ada MAC address, skip")
            continue
        

        category = kategori_log(data_log)
        if not category:
            print("DEBUG: Tidak ada kategori, skip")
            continue
        

        message = format_message(data_log, category)
        print(f"DEBUG: Message formatted: {message}")
        
        await send_to_telegram(message, category, bot, CHAT_IDS, data_log)

async def main():
    """Main function"""
    try:
        await monitor_log()
    except KeyboardInterrupt:
        print("Bot dihentikan")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Starting OLT Monitor Bot...")
    asyncio.run(main())
