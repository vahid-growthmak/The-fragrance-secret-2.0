#!/usr/bin/env python3
"""Phase 2 — copy metafield DEFINITIONS from the dev store to the live store.

Definitions are store-level schema and do not travel with theme code, so the
new theme's sections would render blank without them. This copies only
definitions that are missing on live, and only from the `custom` namespace.

Deliberately excluded:
  test_data.*   Shopify's snowboard sample data, present on the dev store
                because it is a development store. Nothing reads it and it
                has no business on a production catalogue.
  everything else outside `custom`
                the live store already owns 54 definitions of its own
                (Shopify's taxonomy, Google Shopping, Judge.me). Those are
                left exactly as they are.

Values are NOT written here — this is schema only. A definition with no
values changes nothing on the storefront.

    python3 scripts/migrate-metafield-definitions.py            # dry run
    python3 scripts/migrate-metafield-definitions.py --apply    # create
"""

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAMESPACE = "custom"
SKIP_NAMESPACES = {"test_data"}

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env():
    env = {}
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
VER = ENV.get("SHOPIFY_API_VERSION", "2024-10")
LIVE = (ENV["SHOPIFY_STORE_DOMAIN"].replace("https://", "").strip("/"), ENV["SHOPIFY_ADMIN_ACCESS_TOKEN"])
DEV = (ENV["DEV_SHOPIFY_STORE_DOMAIN"], ENV["DEV_SHOPIFY_ADMIN_ACCESS_TOKEN"])


def gql(store, query, variables=None):
    dom, tok = store
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(f"https://{dom}/admin/api/{VER}/graphql.json", data=body,
                                 method="POST", headers={"X-Shopify-Access-Token": tok,
                                                         "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=90, context=SSL_CTX).read())
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 5):
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("retries exhausted")


LIST_Q = """query($o:MetafieldOwnerType!,$c:String){
  metafieldDefinitions(first:100, ownerType:$o, after:$c){
    pageInfo{hasNextPage endCursor}
    nodes{ name namespace key description type{ name } ownerType
      validations{ name value } } } }"""

CREATE = """mutation($d:MetafieldDefinitionInput!){
  metafieldDefinitionCreate(definition:$d){
    createdDefinition{ id name namespace key type{ name } }
    userErrors{ field message code } } }"""

OWNERS = ["PRODUCT", "PRODUCTVARIANT", "COLLECTION", "SHOP", "PAGE"]


def fetch(store):
    out = []
    for owner in OWNERS:
        cur = None
        while True:
            d = gql(store, LIST_Q, {"o": owner, "c": cur})["metafieldDefinitions"]
            for n in d["nodes"]:
                n["ownerType"] = owner
            out += d["nodes"]
            if not d["pageInfo"]["hasNextPage"]:
                break
            cur = d["pageInfo"]["endCursor"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    live, dev = fetch(LIVE), fetch(DEV)
    k = lambda d: (d["ownerType"], d["namespace"], d["key"])
    L = {k(d) for d in live}
    plan, skipped = [], []
    for d in dev:
        if k(d) in L:
            continue
        if d["namespace"] in SKIP_NAMESPACES:
            skipped.append(d)
            continue
        if d["namespace"] != NAMESPACE:
            skipped.append(d)
            continue
        plan.append(d)

    print(f"live: {LIVE[0]}  ({len(live)} definitions)")
    print(f"dev : {DEV[0]}  ({len(dev)} definitions)\n")
    print(f"TO CREATE on live ({len(plan)}):")
    for d in sorted(plan, key=lambda x: (x["ownerType"], x["key"])):
        v = ", ".join(f"{x['name']}={x['value'][:22]}" for x in (d["validations"] or [])) or "-"
        print(f"   {d['ownerType']:<9} {d['namespace']}.{d['key']:<22} {d['type']['name']:<24} "
              f"name={d['name'][:22]!r} validations={v}")
    print(f"\nDELIBERATELY SKIPPED ({len(skipped)}):")
    for d in skipped:
        print(f"   {d['ownerType']:<9} {d['namespace']}.{d['key']:<22} {d['type']['name']}")

    out = REPO / "scripts" / "metafield-definitions-plan.json"
    out.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nfull plan -> {out.relative_to(REPO)}")

    if not args.apply:
        print("\n[dry run — nothing created. Re-run with --apply.]")
        return
    if not plan:
        print("nothing to do")
        return

    print(f"\nAbout to create {len(plan)} metafield definitions on {LIVE[0]} (schema only, no values).")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing created")

    ok = fail = 0
    log = []
    for n, d in enumerate(plan, 1):
        inp = {"name": d["name"], "namespace": d["namespace"], "key": d["key"],
               "type": d["type"]["name"], "ownerType": d["ownerType"]}
        if d.get("description"):
            inp["description"] = d["description"]
        if d.get("validations"):
            inp["validations"] = [{"name": v["name"], "value": v["value"]} for v in d["validations"]]
        try:
            res = gql(LIVE, CREATE, {"d": inp})["metafieldDefinitionCreate"]
            errs = res.get("userErrors") or []
            if errs:
                fail += 1
                log.append({"key": f"{d['namespace']}.{d['key']}", "errors": errs})
                print(f"  [{n}/{len(plan)}] FAIL {d['namespace']}.{d['key']}: {errs[:1]}")
            else:
                ok += 1
                log.append({"key": f"{d['namespace']}.{d['key']}",
                            "id": res["createdDefinition"]["id"]})
                print(f"  [{n}/{len(plan)}] ok   {d['namespace']}.{d['key']}")
        except Exception as e:
            fail += 1
            log.append({"key": f"{d['namespace']}.{d['key']}", "errors": str(e)[:200]})
            print(f"  [{n}/{len(plan)}] FAIL {d['namespace']}.{d['key']}: {e}")
        time.sleep(0.3)
    runlog = REPO / "scripts" / "metafield-definitions-run.json"
    runlog.write_text(json.dumps({"created": ok, "failed": fail, "log": log}, indent=1), encoding="utf-8")
    print(f"\ncreated {ok}, failed {fail} -> {runlog.relative_to(REPO)}")


if __name__ == "__main__":
    main()
