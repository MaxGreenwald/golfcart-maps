-- gcm-analytics: anonymous usage events. No IPs, no cookies, no personal data.
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,          -- ms since epoch (server time)
  event TEXT NOT NULL,
  region TEXT,
  props TEXT,                   -- JSON
  uid TEXT,                     -- anonymous random id (localStorage)
  sid TEXT,                     -- anonymous random session id (30 min idle)
  device TEXT,                  -- mobile | tablet | desktop
  pwa INTEGER,                  -- 1 = standalone home-screen app
  country TEXT                  -- from request.cf.country
);
CREATE INDEX IF NOT EXISTS ev_ts ON events(ts);
CREATE INDEX IF NOT EXISTS ev_event_ts ON events(event,ts);
