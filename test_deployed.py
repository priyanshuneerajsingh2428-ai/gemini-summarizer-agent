#!/usr/bin/env python3
"""
test_deployed.py — Smoke-test the deployed Cloud Run agent.

Usage:
    python test_deployed.py --url https://<your-cloud-run-url>
    python test_deployed.py --url http://localhost:8080   # local test
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

SAMPLE_TEXT = (
    "Artificial intelligence (AI) is transforming industries at an unprecedented pace. "
    "From healthcare diagnostics to autonomous vehicles, machine learning models are "
    "being embedded into critical systems. However, this rapid adoption raises important "
    "questions about safety, transparency, and accountability. Researchers and policymakers "
    "are now racing to establish frameworks that ensure AI systems are fair, explainable, "
    "and aligned with human values. The next decade will be decisive in determining whether "
    "AI becomes a tool for broad human flourishing or a source of new inequalities."
)


def ok(label: str):
    print(f"  {GREEN}✅  {label}{RESET}")


def fail(label: str, detail: str = ""):
    print(f"  {RED}❌  {label}{RESET}")
    if detail:
        print(f"      {detail}")


def post(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def get(url: str, timeout: int = 15) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser(description="Smoke-test the deployed ADK agent.")
    parser.add_argument("--url", required=True, help="Base URL of the deployed service.")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    errors = 0

    print(f"\n{BOLD}{'═'*55}{RESET}")
    print(f"{BOLD}  ADK Summarizer Agent — Smoke Tests{RESET}")
    print(f"{BOLD}{'═'*55}{RESET}")
    print(f"  Target: {BLUE}{base}{RESET}\n")

    # ── Test 1: Health check ──────────────────────────────────────────────
    print(f"{BOLD}[1] Health check — GET /{RESET}")
    try:
        data = get(f"{base}/")
        assert data.get("status") == "ok", f"Unexpected status: {data}"
        ok(f"status=ok, agent={data.get('agent')}, model={data.get('model')}")
    except Exception as e:
        fail("Health check failed", str(e))
        errors += 1

    # ── Test 2: Agent card ────────────────────────────────────────────────
    print(f"\n{BOLD}[2] Agent card — GET /agent-card{RESET}")
    try:
        data = get(f"{base}/agent-card")
        assert data.get("name") == "summarizer_agent"
        ok(f"Agent card returned. Capabilities: {data.get('capabilities')}")
    except Exception as e:
        fail("Agent card failed", str(e))
        errors += 1

    # ── Test 3: Summarize — bullet style ─────────────────────────────────
    print(f"\n{BOLD}[3] Summarize — bullet style — POST /summarize{RESET}")
    try:
        data = post(f"{base}/summarize", {"text": SAMPLE_TEXT, "style": "bullet"})
        assert data.get("summary"), "Empty summary"
        assert isinstance(data.get("key_topics"), list), "key_topics must be a list"
        ok(f"Summary: {data['summary'][:80]}…")
        ok(f"Word count: {data['word_count']} | Topics: {data['key_topics']}")
        ok(f"Sentiment: {data['sentiment']}")
    except Exception as e:
        fail("Bullet summarize failed", str(e))
        errors += 1

    # ── Test 4: Summarize — paragraph style ──────────────────────────────
    print(f"\n{BOLD}[4] Summarize — paragraph style — POST /summarize{RESET}")
    try:
        data = post(f"{base}/summarize", {"text": SAMPLE_TEXT, "style": "paragraph"})
        assert data.get("summary")
        ok(f"Summary (paragraph): {data['summary'][:80]}…")
    except Exception as e:
        fail("Paragraph summarize failed", str(e))
        errors += 1

    # ── Test 5: Validation — empty text ──────────────────────────────────
    print(f"\n{BOLD}[5] Validation — empty text (expect 422){RESET}")
    try:
        req = urllib.request.Request(
            f"{base}/summarize",
            data=json.dumps({"text": "", "style": "bullet"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            fail("Expected 422 but got 200")
            errors += 1
        except urllib.error.HTTPError as e:
            if e.code == 422:
                ok("Correctly returned 422 for empty text.")
            else:
                fail(f"Wrong status code: {e.code}")
                errors += 1
    except Exception as e:
        fail("Validation test error", str(e))
        errors += 1

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*55}{RESET}")
    if errors == 0:
        print(f"{GREEN}{BOLD}  All tests passed! 🎉{RESET}")
    else:
        print(f"{RED}{BOLD}  {errors} test(s) failed.{RESET}")
    print(f"{BOLD}{'═'*55}{RESET}\n")

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
