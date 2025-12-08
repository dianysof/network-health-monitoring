from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, AnyUrl, EmailStr
import os
import psycopg
from psycopg.rows import dict_row
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import time
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Network Health API (MVP)")

# Allow frontend (Vite) to call this API from the browser
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://209.38.10.37",
    # Si luego tienes frontend en otro dominio, lo agregas aquí.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Auth / JWT settings ===
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")  # TODO: override in real deployment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# === Auth Models ===
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime


# === DB config ===
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "nethealth")
DB_USER = os.getenv("DB_USER", "netuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "netpass")


def get_conn():
    # Simple connection per request for MVP (we’ll optimize later)
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )


def get_user_by_email(email: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email=%s;",
                (email,),
            )
            return cur.fetchone()


def get_user_by_id(user_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE id=%s;",
                (user_id,),
            )
            return cur.fetchone()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception

        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


# ================================
# AUTH ENDPOINTS
# ================================

@app.post("/signup", response_model=UserOut)
def signup(user_in: UserCreate):
    existing = get_user_by_email(user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = get_password_hash(user_in.password)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email, created_at;
                """,
                (user_in.email, password_hash),
            )
            row = cur.fetchone()
            conn.commit()

    return row


@app.post("/login", response_model=Token)
def login(user_in: UserLogin):
    user = get_user_by_email(user_in.email)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not verify_password(user_in.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": str(user["id"])})
    return {"access_token": access_token, "token_type": "bearer"}


# ================================
# HEALTH CHECK
# ================================

@app.get("/healthz")
def healthz():
    """Liveness/readiness check (later used by Kubernetes)."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                _ = cur.fetchone()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# ENDPOINTS CRUD
# ================================

@app.get("/api/endpoints")
def list_endpoints(current_user=Depends(get_current_user)):
    """
    List all endpoints owned by the authenticated user.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.id, e.name, e.url, e.created_at
                FROM endpoints e
                WHERE e.user_id = %s
                ORDER BY e.id;
                """,
                (current_user["id"],),
            )
            rows = cur.fetchall()
    return {"endpoints": rows}


class NewEndpoint(BaseModel):
    name: str
    url: AnyUrl


@app.post("/api/endpoints")
def create_endpoint(
    ep: NewEndpoint,
    current_user=Depends(get_current_user),
):
    """
    Create a new endpoint owned by the authenticated user.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO endpoints (user_id, name, url)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, name, url, created_at,
                          latency_threshold_ms,
                          consecutive_fail_threshold,
                          consecutive_failures,
                          alert_active,
                          last_alert_at;
                """,
                (current_user["id"], ep.name, str(ep.url)),
            )
            row = cur.fetchone()
            conn.commit()

    return row


class EndpointUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[AnyUrl] = None


@app.put("/api/endpoints/{endpoint_id}")
def update_endpoint(
    endpoint_id: int,
    ep_update: EndpointUpdate,
    current_user=Depends(get_current_user),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute(
                "SELECT id FROM endpoints WHERE id = %s AND user_id = %s;",
                (endpoint_id, current_user["id"]),
            )
            owned = cur.fetchone()
            if owned is None:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            fields = []
            params = []

            if ep_update.name is not None:
                fields.append("name = %s")
                params.append(ep_update.name)

            if ep_update.url is not None:
                fields.append("url = %s")
                params.append(str(ep_update.url))

            if not fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            params.append(endpoint_id)

            cur.execute(
                f"""
                UPDATE endpoints
                SET {", ".join(fields)}
                WHERE id = %s
                RETURNING id, user_id, name, url, created_at,
                          latency_threshold_ms,
                          consecutive_fail_threshold,
                          consecutive_failures,
                          alert_active,
                          last_alert_at;
                """,
                params,
            )
            row = cur.fetchone()
            conn.commit()

    return row


@app.delete("/api/endpoints/{endpoint_id}")
def delete_endpoint(
    endpoint_id: int,
    current_user=Depends(get_current_user),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM endpoints
                WHERE id = %s AND user_id = %s
                RETURNING id;
                """,
                (endpoint_id, current_user["id"]),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Endpoint not found")
            conn.commit()

    return {"message": "Endpoint deleted"}


# ================================
# MEASUREMENTS (generic list + worker insert)
# ================================

@app.get("/api/measurements")
def list_measurements(endpoint_id: Optional[int] = None, limit: int = 50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if endpoint_id is not None:
                cur.execute(
                    """
                    SELECT m.id, m.endpoint_id, m.latency_ms, m.status, m.observed_at
                    FROM measurements m
                    WHERE m.endpoint_id=%s
                    ORDER BY m.observed_at DESC
                    LIMIT %s;
                    """,
                    (endpoint_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT m.id, m.endpoint_id, m.latency_ms, m.status, m.observed_at
                    FROM measurements m
                    ORDER BY m.observed_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
    return {"measurements": rows}


class NewMeasurement(BaseModel):
    endpoint_id: int
    latency_ms: int
    status: str  # 'up' | 'down'


@app.post("/api/measurements")
def add_measurement(m: NewMeasurement):
    if m.status not in ("up", "down"):
        raise HTTPException(400, "status must be 'up' or 'down'")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM endpoints WHERE id=%s;", (m.endpoint_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "endpoint not found")
            cur.execute(
                """
                INSERT INTO measurements (endpoint_id, latency_ms, status)
                VALUES (%s, %s, %s)
                RETURNING id, endpoint_id, latency_ms, status, observed_at;
                """,
                (m.endpoint_id, m.latency_ms, m.status),
            )
            row = cur.fetchone()
            conn.commit()
    return row


# ================================
# SUMMARY (latest measurement per endpoint)
# ================================

class EndpointSummary(BaseModel):
    id: int
    name: str
    url: AnyUrl
    last_status: Optional[str] = None
    last_latency_ms: Optional[int] = None
    last_observed_at: Optional[datetime] = None
    alert: bool = False


@app.get("/api/endpoints/summary")
def endpoints_summary(current_user=Depends(get_current_user)):
    """
    Returns one row per endpoint (OWNED BY THE CURRENT USER)
    with its latest measurement (if any) and alert flag.
    Perfect for the dashboard main table.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id,
                    e.name,
                    e.url,
                    e.alert_active AS alert,
                    m.status AS last_status,
                    m.latency_ms AS last_latency_ms,
                    m.observed_at AS last_observed_at
                FROM endpoints e
                LEFT JOIN LATERAL (
                    SELECT status, latency_ms, observed_at
                    FROM measurements
                    WHERE endpoint_id = e.id
                    ORDER BY observed_at DESC
                    LIMIT 1
                ) m ON TRUE
                WHERE e.user_id = %s
                ORDER BY e.id;
                """,
                (current_user["id"],),
            )
            rows = cur.fetchall()

    summaries = [EndpointSummary(**row) for row in rows]
    return {"endpoints": summaries}


# ================================
# MANUAL MEASURE (API-triggered)
# ================================

@app.post("/api/endpoints/{endpoint_id}/measure")
def manual_measure(
    endpoint_id: int,
    current_user=Depends(get_current_user),
):
    """
    Trigger an immediate measurement for a given endpoint
    owned by the authenticated user.
    """
    # 1) Confirm ownership and get URL
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT url
                FROM endpoints
                WHERE id = %s AND user_id = %s;
                """,
                (endpoint_id, current_user["id"]),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    url = row["url"]

    # 2) Perform HTTP request and measure latency
    start = time.time()
    try:
        resp = requests.get(url, timeout=5)
        latency_ms = int((time.time() - start) * 1000)
        status = "up" if resp.status_code < 500 else "down"
    except Exception:
        latency_ms = None
        status = "down"

    # 3) Store measurement in DB
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO measurements (endpoint_id, latency_ms, status)
                VALUES (%s, %s, %s)
                RETURNING id, endpoint_id, latency_ms, status, observed_at;
                """,
                (endpoint_id, latency_ms, status),
            )
            measurement_row = cur.fetchone()
            conn.commit()

    return measurement_row


# ================================
# HISTORICAL MEASUREMENTS (per endpoint + auth)
# ================================

@app.get("/api/endpoints/{endpoint_id}/measurements")
def get_endpoint_measurements(
    endpoint_id: int,
    limit: int = 50,
    current_user=Depends(get_current_user),
):
    """
    Returns the last N measurements for a given endpoint,
    but only if it belongs to the authenticated user.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute(
                "SELECT id FROM endpoints WHERE id = %s AND user_id = %s;",
                (endpoint_id, current_user["id"]),
            )
            owned = cur.fetchone()
            if owned is None:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            # Get last measurements
            cur.execute(
                """
                SELECT status, latency_ms, observed_at
                FROM measurements
                WHERE endpoint_id = %s
                ORDER BY observed_at DESC
                LIMIT %s;
                """,
                (endpoint_id, limit),
            )
            rows = cur.fetchall()

    return {
        "endpoint_id": endpoint_id,
        "measurements": [
            {
                "status": r["status"],
                "latency_ms": r["latency_ms"],
                "observed_at": r["observed_at"].isoformat() if r["observed_at"] else None,
            }
            for r in rows
        ],
    }


# ================================
# 24-HOUR STATS (UPTIME + AVG LATENCY)
# ================================

@app.get("/api/endpoints/{endpoint_id}/stats")
def get_endpoint_stats(
    endpoint_id: int,
    hours: int = 24,
    current_user=Depends(get_current_user),
):
    """
    Compute uptime % and average latency over a time window (default 24h)
    for a given endpoint owned by the current user.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute(
                "SELECT id FROM endpoints WHERE id = %s AND user_id = %s;",
                (endpoint_id, current_user["id"]),
            )
            owned = cur.fetchone()
            if owned is None:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            # Get measurements within window
            cur.execute(
                """
                SELECT status, latency_ms, observed_at
                FROM measurements
                WHERE endpoint_id = %s
                  AND observed_at >= %s
                ORDER BY observed_at DESC;
                """,
                (endpoint_id, cutoff),
            )
            rows = cur.fetchall()

    if not rows:
        return {
            "endpoint_id": endpoint_id,
            "uptime_percent": None,
            "avg_latency_ms": None,
            "total_checks": 0,
            "window_hours": hours,
        }

    total_checks = len(rows)
    up_count = sum(
        1 for r in rows
        if (r["status"] or "").lower() == "up"
    )

    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    return {
        "endpoint_id": endpoint_id,
        "uptime_percent": round(up_count * 100 / total_checks, 1),
        "avg_latency_ms": round(avg_latency, 1) if avg_latency is not None else None,
        "total_checks": total_checks,
        "window_hours": hours,
    }


# ================================
# ALERT CONFIG + ALERT HISTORY
# ================================

class AlertConfig(BaseModel):
    latency_threshold_ms: int
    consecutive_fail_threshold: int


class AlertConfigOut(AlertConfig):
    consecutive_failures: int
    alert_active: bool
    last_alert_at: Optional[datetime]


@app.get("/api/endpoints/{endpoint_id}/alert-config", response_model=AlertConfigOut)
def get_alert_config(
    endpoint_id: int,
    current_user=Depends(get_current_user),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    latency_threshold_ms,
                    consecutive_fail_threshold,
                    consecutive_failures,
                    alert_active,
                    last_alert_at
                FROM endpoints
                WHERE id = %s AND user_id = %s;
                """,
                (endpoint_id, current_user["id"]),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    return {
        "latency_threshold_ms": row["latency_threshold_ms"],
        "consecutive_fail_threshold": row["consecutive_fail_threshold"],
        "consecutive_failures": row["consecutive_failures"],
        "alert_active": row["alert_active"],
        "last_alert_at": row["last_alert_at"],
    }


@app.put("/api/endpoints/{endpoint_id}/alert-config", response_model=AlertConfigOut)
def update_alert_config(
    endpoint_id: int,
    cfg: AlertConfig,
    current_user=Depends(get_current_user),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE endpoints
                SET latency_threshold_ms = %s,
                    consecutive_fail_threshold = %s
                WHERE id = %s AND user_id = %s
                RETURNING
                    latency_threshold_ms,
                    consecutive_fail_threshold,
                    consecutive_failures,
                    alert_active,
                    last_alert_at;
                """,
                (
                    cfg.latency_threshold_ms,
                    cfg.consecutive_fail_threshold,
                    endpoint_id,
                    current_user["id"],
                ),
            )
            row = cur.fetchone()
            conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    return {
        "latency_threshold_ms": row["latency_threshold_ms"],
        "consecutive_fail_threshold": row["consecutive_fail_threshold"],
        "consecutive_failures": row["consecutive_failures"],
        "alert_active": row["alert_active"],
        "last_alert_at": row["last_alert_at"],
    }


class AlertOut(BaseModel):
    id: int
    endpoint_id: int
    type: str
    message: str
    value: Optional[int]
    created_at: datetime


@app.get("/api/endpoints/{endpoint_id}/alerts")
def get_endpoint_alerts(
    endpoint_id: int,
    limit: int = 50,
    current_user=Depends(get_current_user),
):
    """
    Returns the most recent alert events for a given endpoint.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check ownership
            cur.execute(
                "SELECT id FROM endpoints WHERE id = %s AND user_id = %s;",
                (endpoint_id, current_user["id"]),
            )
            owned = cur.fetchone()
            if owned is None:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            # Get alerts
            cur.execute(
                """
                SELECT id, endpoint_id, type, message, value, created_at
                FROM alerts
                WHERE endpoint_id = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (endpoint_id, limit),
            )
            rows = cur.fetchall()

    return {"endpoint_id": endpoint_id, "alerts": rows}
