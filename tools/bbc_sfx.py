#!/usr/bin/env python3
"""Search and fetch BBC Sound Effects (https://sound-effects.bbcrewind.co.uk).

Licence: RemArc, personal, educational and research use only. Fine for Yggdrasil
(personal), but the recordings must not be used commercially or redistributed for profit.

    bbc_sfx.py search "drinking horn" [n]      list id, seconds, description
    bbc_sfx.py get ID OUT.wav                  download the original WAV (falls back to the 128k MP3)
"""
import json
import sys
import urllib.request

API = "https://sound-effects-api.bbcrewind.co.uk/api/sfx/search"
UA = {"User-Agent": "YggdrasilSounds/1.0 (personal project)", "Content-Type": "application/json"}


def search(query, n=12):
    body = {"criteria": {"from": 0, "size": n, "query": query, "tags": None, "categories": None,
                         "durations": None, "continents": None, "sortBy": None, "source": None,
                         "recordist": None, "habitat": None}}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers=UA, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.load(r)["results"]
    for x in res:
        print(f'{x["id"]}  {x["duration"] / 1000:7.1f}s  {x["description"][:110]}')


def get(sid, out):
    for url in (f"https://sound-effects-media.bbcrewind.co.uk/wav/{sid}.wav",
                f"https://sound-effects-media.bbcrewind.co.uk/mp3/{sid}.mp3"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
            with urllib.request.urlopen(req, timeout=60) as r, open(out if url.endswith(".wav") else out + ".mp3", "wb") as f:
                f.write(r.read())
            print("saved", url.rsplit("/", 1)[1])
            return
        except Exception as e:
            print("no", url.rsplit("/", 1)[1], e)
    sys.exit(1)


if __name__ == "__main__":
    if sys.argv[1] == "search":
        search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12)
    else:
        get(sys.argv[2], sys.argv[3])
