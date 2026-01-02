import logging
import pymysql as mysql

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ONUCleanup")

# ---------------- DB CONFIG ----------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "",
    "password": "",
    "database": "db_mng_olt",
    "autocommit": True
}

# ---------------- SETTING ----------------
RETENTION_DAYS = 30  
TABLE_NAME = "onu_log"  

# ---------------- MAIN ----------------
def main():
    conn = mysql.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        logger.info(f"Start cleanup data > {RETENTION_DAYS} hari di table {TABLE_NAME}")


        cur.execute(f"""
            SELECT COUNT(*) 
            FROM {TABLE_NAME}
            WHERE created_at < NOW() - INTERVAL %s DAY
        """, (RETENTION_DAYS,))
        total = cur.fetchone()[0]

        if total == 0:
            logger.info("Tidak ada data lama yang perlu dihapus")
            return

        logger.info(f"Data yang akan dihapus: {total}")


        cur.execute(f"""
            DELETE FROM {TABLE_NAME}
            WHERE created_at < NOW() - INTERVAL %s DAY
        """, (RETENTION_DAYS,))

        conn.commit()
        logger.info(f"Cleanup selesai, {total} row dihapus")

    except Exception as e:
        logger.error(f"Gagal cleanup data: {e}")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
