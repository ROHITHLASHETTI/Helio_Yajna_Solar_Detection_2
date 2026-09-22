"""
Production SQLite Database Layer with System Design Optimizations.
Features:
  - SQLite WAL (Write-Ahead-Logging) mode for high-concurrency read/write
  - Memory-mapped I/O (mmap_size = 256MB)
  - Compound indices on frequently filtered attributes (locality, coordinates, status)
  - Thread-safe connection manager
  - Automatic database initialization & realistic seeding based on Helio Yajna Blueprint
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_DIR = Path(__file__).parent.parent / "database_store"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "helio_yajna.db"


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=20.0)
    conn.row_factory = sqlite3.Row
    # System design performance pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA mmap_size = 268435456;") # 256MB memory map
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initializes schema and tables if not already existing."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL, -- 'common' | 'discom' | 'admin'
            organization TEXT,
            service_area TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 2. Sites
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sample_id TEXT,
            title TEXT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            address TEXT,
            locality TEXT NOT NULL DEFAULT 'Locality A',
            circle TEXT DEFAULT 'South Circle',
            division TEXT DEFAULT 'Metro Division',
            sanctioned_load_kw REAL DEFAULT 5.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        );
        """)

        # 3. Analyses (AI verification results)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            user_id INTEGER,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            has_solar INTEGER NOT NULL, -- 1 or 0
            confidence REAL NOT NULL,
            pv_area_sqm_est REAL NOT NULL,
            capacity_kw_est REAL NOT NULL,
            euclidean_distance_m_est REAL DEFAULT 0.0,
            buffer_radius_sqft INTEGER DEFAULT 1200,
            qc_status TEXT NOT NULL, -- 'VERIFIABLE' | 'NOT_VERIFIABLE'
            detection_method TEXT NOT NULL,
            bbox_json TEXT,
            image_base64 TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        );
        """)

        # 4. Energy Records (Monthly/Yearly generation)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            locality TEXT NOT NULL,
            period TEXT NOT NULL, -- '2025-01', '2025-02', etc.
            estimated_kwh REAL NOT NULL,
            actual_kwh REAL,
            source_type TEXT NOT NULL, -- 'meter' | 'inverter' | 'estimated'
            status TEXT NOT NULL DEFAULT 'normal', -- 'normal' | 'underperforming' | 'overperforming'
            recorded_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE
        );
        """)

        # 5. Issues (Installation & Operation tracking)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            locality TEXT NOT NULL,
            title TEXT NOT NULL,
            issue_type TEXT NOT NULL, -- 'installation_delay', 'documentation_gap', 'site_mismatch', 'generation_issue', 'ai_review', 'data_quality'
            severity TEXT NOT NULL, -- 'low', 'medium', 'high', 'critical'
            status TEXT NOT NULL, -- 'open', 'assigned', 'in_progress', 'evidence_added', 'resolved', 'closed'
            age_days INTEGER DEFAULT 1,
            assigned_team TEXT,
            resolution_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE
        );
        """)

        # 6. Irregularities (Review queue)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS irregularities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            analysis_id INTEGER,
            locality TEXT NOT NULL,
            signal_type TEXT NOT NULL, -- 'low_confidence', 'unregistered_solar', 'capacity_mismatch', 'generation_anomaly', 'missing_meter_data'
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_review', -- 'pending_review', 'investigating', 'resolved', 'dismissed'
            evidence_json TEXT,
            reviewer_notes TEXT,
            reviewer_name TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE,
            FOREIGN KEY (analysis_id) REFERENCES analyses (id) ON DELETE CASCADE
        );
        """)

        # 7. Recommendations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            site_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL, -- 'cleaning', 'shading', 'inverter', 'efficiency'
            potential_gain_percent REAL DEFAULT 15.0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE
        );
        """)

        # 8. Messages / Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'info', -- 'info' | 'alert' | 'success'
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)

        # Performance Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sites_coords ON sites(lat, lon);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sites_locality ON sites(locality);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_site ON analyses(site_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_has_solar ON analyses(has_solar);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_energy_site_period ON energy_records(site_id, period);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_irregularities_status ON irregularities(status);")

    # Seed baseline accounts & blueprint operational data if empty
    seed_initial_data()


def seed_initial_data():
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if users already seeded
        cursor.execute("SELECT COUNT(*) as count FROM users;")
        if cursor.fetchone()["count"] > 0:
            return

        now = datetime.now().isoformat()

        # 1. Seed Users
        cursor.execute("""
        INSERT INTO users (email, password, name, role, organization, service_area, created_at)
        VALUES 
        ('citizen@helio.energy', 'helio123', 'Rajesh Sharma', 'common', 'Green Homeowner', 'Adyar, Chennai', ?),
        ('analyst@discom.gov.in', 'discom123', 'A. K. Sundaram', 'discom', 'TANGEDCO Metro', 'Chennai Distribution Circle', ?),
        ('admin@helio.energy', 'admin123', 'Platform Administrator', 'admin', 'Helio Yajna HQ', 'National', ?);
        """, (now, now, now))

        common_uid = 1

        # 2. Seed Common User's primary site (Vardhaman College Rooftop / Residential Solar Site)
        cursor.execute("""
        INSERT INTO sites (user_id, sample_id, title, lat, lon, address, locality, circle, division, sanctioned_load_kw, created_at)
        VALUES (?, 'SITE-2025-01', 'Green Villa Rooftop', 17.2608, 78.3072, 'Vardhaman College Campus, Kacharam, Shamshabad, Hyderabad', 'Locality A', 'South Circle', 'Shamshabad Division', 5.0, ?);
        """, (common_uid, now))
        site_id = cursor.lastrowid

        # Seed initial analysis for Common User
        cursor.execute("""
        INSERT INTO analyses (
            site_id, user_id, lat, lon, has_solar, confidence, pv_area_sqm_est,
            capacity_kw_est, euclidean_distance_m_est, buffer_radius_sqft, qc_status,
            detection_method, bbox_json, metadata_json, created_at
        ) VALUES (
            ?, ?, 12.99151, 80.23362, 1, 0.94, 25.4,
            5.08, 1.8, 1200, 'VERIFIABLE',
            'crop_1200', '[[310, 290, 520, 480]]', '{"zoom": 20, "source": "Google Static Maps"}', ?
        );
        """, (site_id, common_uid, now))

        # Seed Monthly Energy Records (Actual vs Estimated for Common User)
        monthly_data = [
            ('2024-09', 580, 595, 'meter', 'normal'),
            ('2024-10', 540, 520, 'meter', 'normal'),
            ('2024-11', 490, 430, 'meter', 'underperforming'),
            ('2024-12', 460, 410, 'meter', 'underperforming'),
            ('2025-01', 520, 510, 'meter', 'normal'),
            ('2025-02', 610, 612, 'meter', 'normal'),
        ]
        for period, est, act, src, status in monthly_data:
            cursor.execute("""
            INSERT INTO energy_records (site_id, locality, period, estimated_kwh, actual_kwh, source_type, status, recorded_at)
            VALUES (?, 'Locality A', ?, ?, ?, ?, ?, ?);
            """, (site_id, period, est, act, src, status, now))

        # Seed Recommendations for Common User
        cursor.execute("""
        INSERT INTO recommendations (user_id, site_id, title, description, category, potential_gain_percent, status, created_at)
        VALUES 
        (?, ?, 'Seasonal Dust & Soiling Clearance', 'Satellite and generation patterns indicate minor soiling loss (~12%). Gentle water wash recommended.', 'cleaning', 12.5, 'active', ?),
        (?, ?, 'Inverter Firmware & Health Check', 'Generation dropped during November rain spells. Run DC isolation test on string 2.', 'inverter', 8.0, 'active', ?);
        """, (common_uid, site_id, now, common_uid, site_id, now))

        # Seed Messages for Common User
        cursor.execute("""
        INSERT INTO messages (user_id, title, content, type, is_read, created_at)
        VALUES 
        (?, 'Monthly Solar Generation Update', 'Your solar system generated 612 kWh in February, outperforming seasonal estimates by 0.3%.', 'success', 0, ?),
        (?, 'AI Verification Completed', 'Rooftop spatial buffer audit confirmed 25.4 m² active panels with 94% confidence.', 'info', 0, ?);
        """, (common_uid, now, common_uid, now))

        # 3. Seed DISCOM Locality Operational Data (as specified in PDF Page 8 & 9)
        # Sites for Locality A, B, C, D
        localities_data = [
            ("Locality A", 1420, 3.8, 12.4, "South Circle"),
            ("Locality B", 980, 2.4, 8.1, "Central Circle"),
            ("Locality C", 1860, 5.1, 16.8, "North Circle"),
            ("Locality D", 740, 1.7, 5.2, "West Circle"),
        ]
        for loc_name, s_count, cap_mw, energy_gwh, circle in localities_data:
            # Add representative sites for map visualization
            coords = {
                "Locality A": (12.9915, 80.2336),
                "Locality B": (13.0405, 80.2435),
                "Locality C": (13.0827, 80.2707),
                "Locality D": (12.9249, 80.1485)
            }.get(loc_name, (13.0, 80.2))

            cursor.execute("""
            INSERT INTO sites (user_id, sample_id, title, lat, lon, address, locality, circle, division, sanctioned_load_kw, created_at)
            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, 'Metro Division', ?, ?);
            """, (f"DISCOM-{loc_name}", f"Substation Feeder - {loc_name}", coords[0], coords[1], f"Grid Area {loc_name}", loc_name, circle, cap_mw * 1000, now))

        # 4. Seed Installation Issues (from PDF Page 10)
        issues_seed = [
            ("Locality A", "Net-Meter Commissioning Delay", "installation_delay", "high", "in_progress", 14, "Metering Team Alpha", "Meter delivered; inspection scheduled for Thursday."),
            ("Locality B", "Missing Commissioning Certificate", "documentation_gap", "medium", "open", 28, "Compliance Bureau", "Consumer notified to submit safety clearance."),
            ("Locality C", "Meter Coordinates Differ from GIS Survey", "site_mismatch", "high", "assigned", 9, "Field Survey Unit 3", "Physical site visit ordered to reconcile lat/lon."),
            ("Locality D", "Persistently Sub-nominal Generation vs Capacity", "generation_issue", "critical", "evidence_added", 42, "Grid Ops Analysis", "Inverter telemetry logs received showing phase drop."),
            ("Locality A", "Low Confidence Detection on Tiled Roof", "ai_review", "low", "open", 3, "AI Audit Team", "Requires aerial zoom 21 or drone confirmation.")
        ]
        for loc, title, itype, sev, stat, age, team, notes in issues_seed:
            cursor.execute("""
            INSERT INTO issues (site_id, locality, title, issue_type, severity, status, age_days, assigned_team, resolution_notes, created_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (loc, title, itype, sev, stat, age, team, notes, now, now))

        # 5. Seed Irregularity Review Queue (from PDF Page 11)
        irregularities_seed = [
            ("Locality B", "unregistered_solar", "high", "pending_review", json.dumps({
                "solar_detected": True,
                "confidence": 0.89,
                "est_capacity_kw": 8.4,
                "sanctioned_load_kw": 0.0,
                "consumer_name": "Metro Commercial Hub",
                "notes": "Large 42 m² array detected on rooftop with no registered net-metering application."
            })),
            ("Locality C", "capacity_mismatch", "critical", "investigating", json.dumps({
                "solar_detected": True,
                "confidence": 0.93,
                "est_capacity_kw": 16.5,
                "sanctioned_load_kw": 5.0,
                "consumer_name": "Sundaram Warehousing",
                "notes": "AI detected 82 m² installation exceeding sanctioned grid feed allowance by 230%."
            })),
            ("Locality D", "generation_anomaly", "medium", "pending_review", json.dumps({
                "solar_detected": True,
                "confidence": 0.82,
                "est_capacity_kw": 6.0,
                "sanctioned_load_kw": 6.0,
                "notes": "Solar panels confirmed physically, but meter records indicate 0 kWh export for 60 days."
            })),
            ("Locality A", "low_confidence", "low", "resolved", json.dumps({
                "solar_detected": True,
                "confidence": 0.52,
                "est_capacity_kw": 3.1,
                "notes": "Vegetation shadow over panel array. Verified as operational during field visit."
            }))
        ]
        for loc, sig_type, sev, stat, ev_json in irregularities_seed:
            cursor.execute("""
            INSERT INTO irregularities (site_id, analysis_id, locality, signal_type, severity, status, evidence_json, created_at, updated_at)
            VALUES (1, 1, ?, ?, ?, ?, ?, ?, ?);
            """, (loc, sig_type, sev, stat, ev_json, now, now))


# Initialize database upon import
init_db()
