import sqlite3
import time
import json
import requests
import datetime

AMIAMI_API_URL = "https://api.amiami.com/api/v1.0/"
DISCORD_WEBHOOK = "https://discord.com/api/v9/webhooks/a/b?wait=true"

con = sqlite3.connect("amiamialert.db")

con.execute("""CREATE TABLE IF NOT EXISTS seen(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gcode STRING NOT NULL UNIQUE,
                last_seen INTEGER NOT NULL)""")

def item_seen_check(gcode: str, seconds_since: int) -> bool:
    return con.execute("SELECT * FROM seen WHERE gcode=? AND last_seen>?", (gcode,int(time.time())-seconds_since)).fetchone() != None

def item_seen_mark(gcode: str):
    res = con.execute("INSERT OR REPLACE INTO seen(gcode, last_seen) VALUES(?, ?)", (gcode,int(time.time())))
    con.commit()

def discord_send(title, url, thumb_url, keyword):
    res = requests.post(DISCORD_WEBHOOK, json={"content": "@everyone", "embeds": [{"description": f"keyword: {keyword}", "url": url, "image": {"url": thumb_url}, "title": title, "timestamp": datetime.datetime.utcnow().isoformat(), "footer": {"text": "A new product in AmiAmi"}}]})
    if res.headers["x-ratelimit-remaining"] == "0":
        time.sleep(float(res.headers["x-ratelimit-reset-after"]))
    if res.status_code == 429:
        time.sleep(float(res.json()["retry_after"]))
        discord_send(title, url, thumb_url, keyword)
        return
    assert res.status_code == 200

def send_item(item, keyword):
    discord_send(item["gname"],
                 f"https://www.amiami.com/eng/detail/?scode={item['gcode']}",
                 f"https://img.amiami.com/{item['thumb_url']}", keyword)

def check_keyword(keyword: str):
    resp = requests.get(AMIAMI_API_URL + f"items?pagemax=50&pagecnt=1&lang=eng&s_keywords={keyword}", headers={"x-user-key": "amiami_dev"})
    items = resp.json()["items"]
    for item in items:
        if item["order_closed_flg"] == 1 or item_seen_check(item["gcode"], 3600*24*7):
            continue
        send_item(item, keyword)
        item_seen_mark(item["gcode"])
with open("keywords", "r") as f:
    for line in f:
        check_keyword(line)

con.close()
