import requests
from bs4 import BeautifulSoup
import psycopg2
from lxml import etree

# The "Inception" page
PORTAL_URL = "https://www.lrs.lt/sip/portal.show?p_r=35391&p_k=1"
DB_PARAMS = {"host": "localhost", "database": "seimas_db", "user": "postgres", "password": "jou"}

def get_all_links():
    print("Searching for all XML links on the portal...")
    response = requests.get(PORTAL_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links starting with the apps.lrs.lt domain
    links = []
    for a in soup.find_all('a', href=True):
        url = a['href']
        if "apps.lrs.lt/sip/p2b" in url:
            links.append(url)
    
    # Remove duplicates
    return list(set(links))

def sync_everything():
    links = get_all_links()
    print(f"Found {len(links)} data feeds!")

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    for url in links:
        # Create a clean name for the feed based on the URL
        feed_name = url.split('.')[-1]
        
        try:
            print(f"Syncing {feed_name}...")
            res = requests.get(url, timeout=10)
            
            # Save the raw XML into our master table
            query = """
            INSERT INTO raw_xml_feeds (feed_name, xml_content, last_synced)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (feed_name) DO UPDATE 
            SET xml_content = EXCLUDED.xml_content, 
                last_synced = CURRENT_TIMESTAMP;
            """
            cur.execute(query, (feed_name, res.text))
            conn.commit()
        except Exception as e:
            print(f"Skipping {feed_name} due to error: {e}")

    cur.close()
    conn.close()
    print("\n--- ALL FEEDS SYNCED ---")

if __name__ == "__main__":
    sync_everything()
