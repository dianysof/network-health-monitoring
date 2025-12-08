import os
import time
import psycopg
from psycopg.rows import dict_row
import requests

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "nethealth")
DB_USER = os.getenv("DB_USER", "netuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "netpass")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "5.0"))


def get_conn():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )


def check_endpoint(url: str, timeout: float = HTTP_TIMEOUT_SECONDS):
    """
    Returns (latency_ms, status_str).
    status_str is 'up' if HTTP 2xx/3xx, otherwise 'down'.
    """
    try:
        start = time.perf_counter()
        resp = requests.get(url, timeout=timeout)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if 200 <= resp.status_code < 400:
            return elapsed_ms, "up"
        else:
            return elapsed_ms, "down"
    except Exception as e:
        # Could not reach endpoint
        print(f"[worker] Error reaching {url}: {e}")
        # None = no latency (consistent con manual_measure del API)
        return None, "down"


def fetch_endpoints(conn):
    """
    Get all endpoints with their alert config/state.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              id,
              name,
              url,
              latency_threshold_ms,
              consecutive_fail_threshold,
              consecutive_failures,
              alert_active
            FROM endpoints
            ORDER BY id;
            """
        )
        return cur.fetchall()


def insert_measurement(conn, endpoint_id: int, latency_ms, status: str):
    """
    Store one measurement row.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO measurements (endpoint_id, latency_ms, status)
            VALUES (%s, %s, %s);
            """,
            (endpoint_id, latency_ms, status),
        )


def update_alert_state(conn, ep, latency_ms, status: str):
    """
    Given the latest check result, update:
      - consecutive_failures
      - alert_active
      - last_alert_at
    and create an entry in alerts si se dispara algo.
    ep es el row completo de endpoints (con config y estado).
    """
    ep_id = ep["id"]
    threshold_latency = ep["latency_threshold_ms"]
    threshold_fail = ep["consecutive_fail_threshold"]
    consecutive_failures = ep["consecutive_failures"] or 0
    alert_active = bool(ep["alert_active"])

    # Actualizar contador de fallos
    if status == "down":
        new_failures = consecutive_failures + 1
    else:
        new_failures = 0

    trigger_alert = False
    alert_type = None
    message = None
    value = None
    new_alert_active = alert_active

    # Caso 1: demasiados "down" seguidos
    if status == "down" and new_failures >= threshold_fail and not alert_active:
        trigger_alert = True
        alert_type = "down"
        message = f"Endpoint is DOWN for {new_failures} consecutive checks"
        value = None
        new_alert_active = True

    # Caso 2: latencia muy alta (solo si está up)
    if (
        status == "up"
        and latency_ms is not None
        and latency_ms > threshold_latency
        and not alert_active
    ):
        trigger_alert = True
        alert_type = "latency"
        message = f"Latency {latency_ms} ms exceeded threshold {threshold_latency} ms"
        value = latency_ms
        new_alert_active = True

    # Caso 3: limpiar alerta cuando se recupera
    if alert_active and status == "up":
        # está up, sin demasiados fallos y dentro del threshold
        if (latency_ms is None or latency_ms <= threshold_latency) and new_failures == 0:
            new_alert_active = False

    with conn.cursor() as cur:
        # Actualizar estado en endpoints
        cur.execute(
            """
            UPDATE endpoints
            SET consecutive_failures = %s,
                alert_active = %s,
                last_alert_at = CASE
                                  WHEN %s THEN NOW()
                                  ELSE last_alert_at
                                END
            WHERE id = %s;
            """,
            (new_failures, new_alert_active, trigger_alert, ep_id),
        )

        # Registrar evento de alerta si se disparó
        if trigger_alert:
            cur.execute(
                """
                INSERT INTO alerts (endpoint_id, type, message, value)
                VALUES (%s, %s, %s, %s);
                """,
                (ep_id, alert_type, message, value),
            )


def main_loop():
    print("[worker] Starting worker loop...")
    while True:
        try:
            with get_conn() as conn:
                endpoints = fetch_endpoints(conn)

                if not endpoints:
                    print("[worker] No endpoints found, sleeping...")
                else:
                    print(f"[worker] Checking {len(endpoints)} endpoints...")

                for ep in endpoints:
                    ep_id = ep["id"]
                    ep_url = ep["url"]
                    ep_name = ep["name"]

                    latency_ms, status = check_endpoint(ep_url)
                    print(
                        f"[worker] {ep_name} ({ep_url}) -> "
                        f"status={status}, latency={latency_ms}ms"
                    )

                    # 1) Insertar medición
                    insert_measurement(conn, ep_id, latency_ms, status)

                    # 2) Actualizar estado de alertas según el resultado
                    update_alert_state(conn, ep, latency_ms, status)

                conn.commit()

        except Exception as e:
            print(f"[worker] Error in loop: {e}")

        # 3. Sleep before next round
        print(f"[worker] Sleeping for {POLL_INTERVAL_SECONDS} seconds...\n")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main_loop()
