"""External evaluation runs — durable, exact-payload benchmark harnesses.

A Horizon *external suite* (schema ``horizon.external_eval/v1``) is a fixed set
of cases whose exact request payloads, source and scorer are pinned by digest.
Horizon stores the suite and immutable run records; it never runs or grades
these cases itself. :class:`ExternalHarness` is the generic runner: it sends
each pinned payload byte for byte, once, keeps a durable per-case checkpoint,
grades the received response with the caller's grader and builds the run
record that ``horizon.suites.import_run`` stores.

The harness talks to one solver endpoint only. It sends no feedback, no grade
and no learning toggle to the node, and it does not read the expected answers:
those stay inside the caller's grader.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._base import HTTPReceipt

SCHEMA = "horizon.external_eval/v1"

Grades = dict[str, dict[str, Any]]
"""``{grade_name: {"passed": True | False | None, "detail": {...}}}`` for one case."""

_HIDDEN = re.compile(r"<(think|reasoning)\b[^>]*>[\s\S]*?(?:</\1>|$)", re.IGNORECASE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def visible_text(text: Any) -> str | None:
    """A response's visible content: inline reasoning blocks removed, ``None`` if absent."""
    if not isinstance(text, str):
        return None
    return _HIDDEN.sub("", text)


def completion_content(doc: Any) -> tuple[str | None, str | None, str | None]:
    """``(raw_content, finish_reason, completion_id)`` of an OpenAI-shaped completion."""
    if not isinstance(doc, Mapping):
        return None, None, None
    choices = doc.get("choices") or [{}]
    choice = choices[0] if isinstance(choices, list) and choices else {}
    message = choice.get("message", {}) if isinstance(choice, Mapping) else {}
    content = message.get("content") if isinstance(message, Mapping) else None
    cid = doc.get("id")
    return (
        content if isinstance(content, str) else None,
        choice.get("finish_reason") if isinstance(choice, Mapping) else None,
        cid if isinstance(cid, str) else None,
    )


def nbot_session_from_completion(completion_id: str | None) -> str | None:
    """The NBot session a completion id names (``chatcmpl-<session>``), unverified."""
    if not completion_id:
        return None
    return completion_id.removeprefix("chatcmpl-") or None


def session_log_verifier(logs_dir: str | os.PathLike[str]) -> Callable[[str], bool]:
    """A verifier that accepts a session only when the node wrote its log file.

    ``logs_dir`` is the isolated node's ``.nconfig/logs`` directory. A session
    id is reported only after this check; it is never invented from a guess.
    """
    root = Path(logs_dir)

    def verify(session_id: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z0-9._-]+", session_id)) and (
            root / f"{session_id}.jsonl"
        ).is_file()

    return verify


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _usage(doc: Any) -> dict[str, Any] | None:
    usage = doc.get("usage") if isinstance(doc, Mapping) else None
    if not isinstance(usage, Mapping):
        return None
    return {k: usage.get(k) if isinstance(usage.get(k), (int, float)) else None
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")}


class ExternalHarness:
    """Run every case of a stored external suite once, durably, and build its run record.

    ``suite`` is the stored definition returned by ``import_suite`` (it carries
    ``definition_sha256``). ``send`` posts exact bytes and returns an
    :class:`HTTPReceipt` (``nbot.Client().chat.completions.send_exact``).
    ``grade(case, receipt)`` returns the case's :data:`Grades` for every grade
    the suite declares. ``verify_session`` (see :func:`session_log_verifier`)
    decides whether the session a completion names really exists on the node.

    Checkpoints live under ``checkpoint_dir/<run_id>/<case_id>/``: the exact
    request bytes, the receipt and the grade. A case whose receipt is already
    on disk is never sent again, so an interrupted run resumes without a
    duplicate inference, and a checkpoint directory belongs to one suite
    digest only.
    """

    def __init__(
        self,
        *,
        suite: Mapping[str, Any],
        run_id: str,
        send: Callable[[bytes], HTTPReceipt],
        grade: Callable[[Mapping[str, Any], HTTPReceipt], Grades],
        checkpoint_dir: str | os.PathLike[str],
        verify_session: Callable[[str], bool] | None = None,
        serialize: Callable[[Mapping[str, Any]], bytes] = lambda r: json.dumps(r).encode(),
        cases: Sequence[str] | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}", run_id):
            raise ValueError("run_id must be 1-128 letters, digits, '.', '_' or '-'")
        if not suite.get("definition_sha256"):
            raise ValueError("suite must be the stored definition returned by import_suite")
        self.suite = suite
        self.run_id = run_id
        self._send = send
        self._grade = grade
        self._verify = verify_session
        self._serialize = serialize
        self.root = Path(checkpoint_dir) / run_id
        wanted = set(cases) if cases else None
        self.cases = [c for c in suite.get("cases", []) if wanted is None or c["id"] in wanted]
        if wanted and len(self.cases) != len(wanted):
            raise ValueError("unknown case ids: " + ", ".join(sorted(wanted - {c["id"] for c in self.cases})))

    def _manifest(self) -> None:
        path = self.root / "manifest.json"
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing.get("suite_definition_sha256") != self.suite["definition_sha256"]:
                raise ValueError(f"{self.root} holds checkpoints of a different suite definition")
            return
        _write(path, {"run_id": self.run_id, "suite_id": self.suite.get("id"),
                      "suite_definition_sha256": self.suite["definition_sha256"],
                      "created_at": utc_now()})

    def _receipt(self, case: Mapping[str, Any]) -> HTTPReceipt:
        folder = self.root / case["id"]
        saved = folder / "receipt.json"
        body = self._serialize(case["request"])
        if saved.exists():
            r = json.loads(saved.read_text(encoding="utf-8"))
            if r["request_sha256"] != sha256_bytes(body):
                raise ValueError(f"checkpoint {folder} was made with a different request")
            return HTTPReceipt(
                method=r["method"], url=r["url"], request_body=body, status=r["status"],
                response_body=r["response_body"].encode("utf-8"), content_type=r["content_type"],
                elapsed_s=r["elapsed_s"], error=r["error"], response_headers=r["response_headers"],
            )
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "request.json").write_bytes(body)
        started = utc_now()
        receipt = self._send(body)
        _write(saved, {
            "method": receipt.method, "url": receipt.url, "request_sha256": sha256_bytes(body),
            "status": receipt.status, "content_type": receipt.content_type,
            "response_body": receipt.response_body.decode("utf-8", errors="replace"),
            "response_headers": receipt.response_headers, "elapsed_s": receipt.elapsed_s,
            "error": receipt.error, "started_utc": started, "finished_utc": utc_now(),
        })
        return receipt

    def run_case(self, case: Mapping[str, Any]) -> dict[str, Any]:
        """Send (or resume) one case and return its run-record case entry."""
        receipt = self._receipt(case)
        doc = receipt.json()
        raw, finish, completion_id = completion_content(doc)
        session = nbot_session_from_completion(completion_id)
        verified = bool(session and self._verify and self._verify(session))
        grades = self._grade(case, receipt)
        _write(self.root / case["id"] / "grade.json", grades)
        error = receipt.error
        if error is None and not receipt.ok:
            error = f"HTTP {receipt.status}"
        return {
            "case_id": case["id"],
            "request": case["request"],
            "http_status": receipt.status,
            "error": error,
            "response_text": visible_text(raw),
            "session_id": session if verified else None,
            "session_ids": [session] if verified else [],
            "grades": grades,
            "metrics": {"request_elapsed_s": round(receipt.elapsed_s, 6), "usage": _usage(doc)},
            "evidence": {
                "completion_id": completion_id,
                "finish_reason": finish,
                "session_verified": verified,
                "request_bytes_sha256": sha256_bytes(receipt.request_body),
                "response_bytes_sha256": sha256_bytes(receipt.response_body),
            },
        }

    def run(
        self, *, statement: str, provenance: Mapping[str, Any] | None = None,
        on_case: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Run every selected case in suite order and return the ``new_run`` record."""
        self._manifest()
        started = time.monotonic()
        rows = []
        for case in self.cases:
            row = self.run_case(case)
            rows.append(row)
            if on_case:
                on_case(row)
        return {
            "schema": SCHEMA,
            "run_id": self.run_id,
            "suite_definition_sha256": self.suite["definition_sha256"],
            "recorded_at": utc_now(),
            "evidence": {"class": "new_run", "dataset_role": self.suite.get("dataset_role"),
                         "statement": statement},
            "provenance": {**(provenance or {}), "harness": "ntropi.evals.ExternalHarness",
                           "checkpoints": str(self.root),
                           "harness_wall_s_this_invocation": round(time.monotonic() - started, 6)},
            "metrics": None,
            "cases": rows,
        }
