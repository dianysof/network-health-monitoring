-- Users of the app (auth will come later)
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Targets to monitor (+ alert config & state)
CREATE TABLE IF NOT EXISTS endpoints (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- ALERT CONFIG
  latency_threshold_ms INT NOT NULL DEFAULT 300,
  consecutive_fail_threshold INT NOT NULL DEFAULT 3,

  -- ALERT STATE (managed by worker)
  consecutive_failures INT NOT NULL DEFAULT 0,
  alert_active BOOLEAN NOT NULL DEFAULT FALSE,
  last_alert_at TIMESTAMPTZ
);

-- Measurements produced by the worker
CREATE TABLE IF NOT EXISTS measurements (
  id SERIAL PRIMARY KEY,
  endpoint_id INT NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
  latency_ms INT,
  status TEXT CHECK (status IN ('up','down')) NOT NULL,
  observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert events history
CREATE TABLE IF NOT EXISTS alerts (
  id SERIAL PRIMARY KEY,
  endpoint_id INT NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
  type TEXT NOT NULL,          -- 'down' | 'latency'
  message TEXT NOT NULL,
  value INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed one test user + endpoint so the API has something to read
INSERT INTO users (email, password_hash)
VALUES ('demo@example.com', 'hash-placeholder')
ON CONFLICT DO NOTHING;

INSERT INTO endpoints (user_id, name, url)
SELECT id, 'Example API', 'https://example.com'
FROM users WHERE email='demo@example.com'
ON CONFLICT DO NOTHING;
