#!/usr/bin/env python3
"""Test rate limiting on vote_api.py POST endpoint."""
import urllib.request
import json

API = "http://localhost:9099/api/votes"
KEY = "Wyp6EhQ0nziVi7HSuq7-h8UDUExCQXCOtPrXupgVwF8"

def post_vote(session_id):
    data = json.dumps({"asset_id": "misc_13", "vote_value": 4, "session_id": session_id}).encode()
    req = urllib.request.Request(API, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-API-Key", KEY)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)

# Test 1: First request should succeed with rate limit headers
print("=== Test 1: Normal POST (expect 201 + X-RateLimit headers) ===")
code, headers = post_vote("rate_test_1")
rl_limit = headers.get("X-RateLimit-Limit", "MISSING")
rl_remaining = headers.get("X-RateLimit-Remaining", "MISSING")
print(f"  Status: {code}")
print(f"  X-RateLimit-Limit: {rl_limit}")
print(f"  X-RateLimit-Remaining: {rl_remaining}")

# Test 2: Burst 30 more requests to hit the limit
print("\n=== Test 2: Burst 30 requests to fill window ===")
ok_count = 0
limited_count = 0
for i in range(30):
    code, headers = post_vote(f"rate_burst_{i}")
    if code == 201:
        ok_count += 1
    elif code == 429:
        limited_count += 1
print(f"  201 OK: {ok_count}")
print(f"  429 Limited: {limited_count}")

# Test 3: Next request should be rate limited
print("\n=== Test 3: 31st request (expect 429) ===")
code, headers = post_vote("rate_should_fail")
retry_after = headers.get("Retry-After", "MISSING")
rl_remaining = headers.get("X-RateLimit-Remaining", "MISSING")
print(f"  Status: {code}")
print(f"  X-RateLimit-Remaining: {rl_remaining}")
print(f"  Retry-After: {retry_after}")

# Test 4: GET should NOT be rate limited
print("\n=== Test 4: GET /api/stats (expect 200, no rate limit) ===")
req = urllib.request.Request("http://localhost:9099/api/stats")
resp = urllib.request.urlopen(req)
print(f"  Status: {resp.status}")

# Summary
print("\n=== SUMMARY ===")
all_pass = True
if code == 429:
    print("  ✅ Rate limiting works — 429 returned after limit")
else:
    print(f"  ❌ Expected 429, got {code}")
    all_pass = False

if rl_limit != "MISSING":
    print(f"  ✅ X-RateLimit-Limit header present: {rl_limit}")
else:
    print("  ❌ X-RateLimit-Limit header missing")
    all_pass = False

if retry_after != "MISSING":
    print(f"  ✅ Retry-After header present: {retry_after}")
else:
    print("  ❌ Retry-After header missing")
    all_pass = False

print(f"\n  {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
