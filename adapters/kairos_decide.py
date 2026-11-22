#!/usr/bin/env python3
"""Score public weekly benchmark features using Minara Cloud's Kairos API."""

import json
import math
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


ENDPOINT = "https://minara.cloud/v1/systemone"
MODEL = "DMIND/Kairos"
QUESTION = "next_7_day_price_direction"
CRITERIA = {
    "up": "The next seven-day return is strictly positive",
    "down": "The next seven-day return is zero or negative",
}
MAX_RESPONSE_BYTES = 65_536


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def score(state, key, opener):
    payload = {
        "model": MODEL,
        "task_profile": "general",
        "state": state,
        "questions": {
            QUESTION: {"type": "choice", "instructions": QUESTION, "criteria": CRITERIA},
        },
    }
    request = Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with opener.open(request, timeout=30) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        with error:
            raise ValueError(f"Minara returned HTTP {error.code}") from None
    except (URLError, OSError):
        raise ValueError("Minara connection failed or timed out") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("Minara response exceeded the size limit")
    try:
        result = json.loads(body)
        answer = result["answers"][QUESTION]
        probabilities = answer["probabilities"]
        choice = answer["choice"]
        kind = answer["type"]
    except (ValueError, TypeError, KeyError):
        raise ValueError("Minara returned an invalid choice response") from None
    if (kind != "choice" or not isinstance(probabilities, dict)
            or probabilities.keys() != CRITERIA.keys()
            or not all(type(p) in (int, float) and 0 <= p <= 1 for p in probabilities.values())
            or not math.isclose(sum(probabilities.values()), 1, rel_tol=0, abs_tol=1e-6)):
        raise ValueError("Minara returned an invalid probability distribution")
    up, down = probabilities["up"], probabilities["down"]
    prediction = "up" if up > down else "down"
    if not isinstance(choice, str) or choice not in CRITERIA or (up != down and choice != prediction):
        raise ValueError("Minara choice disagreed with its probability distribution")

    metadata = {}
    for field in ("model", "model_version", "prompt_version", "calibration_version"):
        value = result.get(field)
        if isinstance(value, str) and key not in value and re.fullmatch(r"[A-Za-z0-9_./-]{1,100}", value):
            metadata[field] = value
    usage = result.get("usage")
    if isinstance(usage, dict):
        for field in ("input_tokens", "output_tokens", "evaluated_questions"):
            value = usage.get(field)
            if type(value) is int and 0 <= value <= MAX_RESPONSE_BYTES:
                metadata[field] = value
    return {"prediction": prediction, "probabilities": probabilities, "api": metadata}


def main():
    key = os.environ.get("KAIROS_API_KEY", "").strip()
    if not key:
        raise SystemExit("KAIROS_API_KEY is required")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            event_id = event["id"]
            state = event["state"]
        except (ValueError, TypeError, KeyError):
            raise SystemExit(f"line {line_number}: invalid JSONL event") from None
        if not isinstance(event_id, str) or not isinstance(state, str) or not state.strip():
            raise SystemExit(f"line {line_number}: expected a string id and nonempty state")
        try:
            result = score(state, key, opener)
        except ValueError as error:
            raise SystemExit(f"line {line_number}: {error}") from None
        print(json.dumps({"id": event_id, **result}, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
