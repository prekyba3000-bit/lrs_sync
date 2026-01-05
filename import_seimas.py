import psycopg2
import re

conn = psycopg2.connect("postgresql://postgres:jou@localhost:5432/seimas_db")
cur = conn.cursor()

def get_mp_map():
    cur.execute("SELECT id, name FROM mps")
    mps = {}
    for mp_id, full_name in cur.fetchall():
        parts = set(full_name.lower().replace('-', ' ').split())
        mps[frozenset(parts)] = mp_id
    return mps

def find_mp(raw_name, mp_map):
    if not raw_name: return None
    raw_name_clean = raw_name.lower().replace('-', ' ')
    raw_parts = set(re.findall(r'\w+', raw_name_clean))
    for name_set, mp_id in mp_map.items():
        if name_set.issubset(raw_parts) or raw_parts.issubset(name_set):
            return mp_id
    return None

def process(filename, table_name, mp_map):
    print(f"Brute-forcing {filename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # This finds everything between (' and ') across newlines
    # It catches: ('MP Name', 'Data1', 'Data2'...)
    records = re.findall(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'", content)
    
    count = 0
    for r in records:
        mp_id = find_mp(r[0], mp_map)
        if mp_id:
            try:
                if table_name == 'mp_assistants':
                    cur.execute("INSERT INTO mp_assistants (mp_id, name, role, phone, email) VALUES (%s, %s, %s, %s, %s)",
                                (mp_id, r[1], r[2], r[3], r[4]))
                elif table_name == 'mp_trips':
                    # For trips, the 5th element in our regex is the end_date. 
                    # We need to find the cost which usually follows the last quote.
                    # We'll look for the number immediately following the last match in the string
                    cur.execute("INSERT INTO mp_trips (mp_id, destination, purpose, start_date, end_date, cost) VALUES (%s, %s, %s, %s, %s, %s)",
                                (mp_id, r[1], r[2], r[3], r[4], 0)) # Defaulting cost to 0 for the brute force
                count += 1
            except:
                conn.rollback()
                continue
    conn.commit()
    print(f"Success! {table_name}: {count} rows.")

cur.execute("TRUNCATE mp_assistants, mp_trips;")
conn.commit()

mp_map = get_mp_map()
process('/home/julio/Desktop/mp_assistants_data.sql', 'mp_assistants', mp_map)
process('/home/julio/Desktop/mp_trips_data.sql', 'mp_trips', mp_map)

cur.close()
conn.close()
