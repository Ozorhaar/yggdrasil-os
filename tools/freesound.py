#!/usr/bin/env python3
"""Search Freesound and fetch high-quality previews, for the realistic Yggdrasil sounds.

The API key is read from $FREESOUND_TOKEN or ~/.config/yggdrasil/freesound.key (never
committed). Each recording keeps its own licence (CC0, CC-BY or CC-BY-NC); credits.py
records them. Personal use.

    freesound.py search "drinking horn toast" [n] [max_seconds]
    freesound.py get ID OUT.ogg        high-quality OGG preview
"""
import json
import os
import sys
import urllib.parse
import urllib.request

LIC = {"publicdomain/zero": "CC0", "licenses/by/": "CC-BY", "licenses/by-nc/": "CC-BY-NC", "sampling+": "Sampling+"}


def token():
    t = os.environ.get("FREESOUND_TOKEN")
    if not t:
        with open(os.path.expanduser("~/.config/yggdrasil/freesound.key")) as f:
            t = f.read().strip()
    return t


def api(path, **params):
    params["token"] = token()
    url = "https://freesound.org/apiv2/" + path + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "YggdrasilSounds/1.0"}), timeout=30) as r:
        return json.load(r)


def short_license(url):
    return next((v for k, v in LIC.items() if k in url), url)


def search(query, n=12, max_s=None):
    flt = f"duration:[0 TO {max_s}]" if max_s else ""
    d = api("search/text/", query=query, page_size=n, filter=flt, sort="score",
            fields="id,name,duration,license,username,avg_rating,num_downloads")
    for r in d["results"]:
        print(f'{r["id"]:>7}  {r["duration"]:6.1f}s  {short_license(r["license"]):9} '
              f'dl{r["num_downloads"]:>6}  {r["name"][:60]}  ({r["username"]})')


def get(sid, out):
    d = api(f"sounds/{sid}/", fields="id,name,license,username,previews,url")
    url = d["previews"]["preview-hq-ogg"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "YggdrasilSounds/1.0"}), timeout=60) as r, open(out, "wb") as f:
        f.write(r.read())
    print(json.dumps({"id": d["id"], "name": d["name"], "user": d["username"],
                      "license": short_license(d["license"]), "url": d["url"]}))


if __name__ == "__main__":
    if sys.argv[1] == "search":
        search(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12, sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        get(sys.argv[2], sys.argv[3])
