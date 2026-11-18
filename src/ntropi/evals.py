"""External evaluation runs — durable, exact-payload benchmark harnesses.

A Horizon *external suite* (schema ``horizon.external_eval/v1``) is a fixed set
of cases whose exact request payloads, source and scorer are pinned by digest.
Horizon stores the suite and immutable run records; it never runs or grades
these cases itself. :class:`ExternalHarness` is the generic runner: it sends
each pinned payload byte for byte, at most once per run, keeps a durable
per-case checkpoint, grades the received response with the caller's grader and
builds the run record that ``horizon.suites.import_run`` stores.

Dispatch contract. Before a case is sent, an exclusive dispatch marker is
written next to its checkpoint. A case with a saved receipt is complete and is
reused. A case with a marker and no receipt was sent (or was being sent) and
its outcome is unknown: the harness never sends it again. It stays pending
until the operator resolves it with :meth:`ExternalHarness.adopt` (a response
recovered from another record) or :meth:`ExternalHarness.abandon` (recorded as
unknown), or starts a new run under a new ``run_id``. An unresolved case is
never reported as passed and never given a session it was not shown to have.

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


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def checked_identifier(value: Any, what: str) -> str:
    """``value`` when it is a safe identifier: letters, digits, ``._-``, starting alphanumeric."""
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or ".." in value:
        raise ValueError(f"{what} {value!r} is not a safe identifier")
    return value


class UnresolvedDispatch(RuntimeError):
    """Cases were dispatched without a saved receipt; their outcome is unknown and they are not resent."""

    def __init__(self, cases: Sequence[str]) -> None:
        self.cases = list(cases)
        super().__init__(
            "dispatch outcome unknown for " + ", ".join(self.cases) +
            "; resolve each with adopt() or abandon(), or start a new run_id")


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
    """Run every case of a stored external suite at most once, durably, and build its run record.

    ``suite`` is the stored definition returned by ``import_suite`` (it carries
    ``definition_sha256``); its case ids are checked and every case is bound
    to its pinned request. ``send`` posts exact bytes and returns an
    :class:`HTTPReceipt` (``nbot.Client().chat.completions.send_exact``).
    ``grade(case, receipt)`` returns the case's :data:`Grades` for every grade
    the suite declares. ``verify_session`` (see :func:`session_log_verifier`)
    decides whether the session a completion names really exists on the node.

    Checkpoints live under ``checkpoint_dir/<run_id>/<case_id>/``: the exact
    request bytes, the dispatch marker, the receipt and the grade. See the
    module's dispatch contract for what happens to an interrupted case.
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
        checked_identifier(run_id, "run_id")
        digest = suite.get("definition_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("suite must be the stored definition returned by import_suite")
        pinned: dict[str, Mapping[str, Any]] = {}
        for case in suite.get("cases", []):
            cid = checked_identifier(case.get("id"), "case id")
            if cid in pinned:
                raise ValueError(f"case id {cid} appears more than once in the suite")
            if not isinstance(case.get("request"), Mapping):
                raise TypeError(f"case {cid} has no pinned request object")
            pinned[cid] = case
        if not pinned:
            raise ValueError("suite has no cases")
        self.suite = suite
        self.run_id = run_id
        self._pinned = pinned
        self._send = send
        self._grade = grade
        self._verify = verify_session
        self._serialize = serialize
        self._grade_names = [g["name"] for g in suite.get("grades", []) if isinstance(g, Mapping)]
        base = Path(checkpoint_dir)
        if base.is_symlink():
            raise ValueError(f"{base} is a symbolic link")
        self._base = base.resolve()
        self.root = self._base / run_id
        if self.root.is_symlink():
            raise ValueError(f"{self.root} is a symbolic link")
        wanted = list(cases) if cases else None
        if wanted:
            unknown = [c for c in wanted if c not in pinned]
            if unknown:
                raise ValueError("unknown case ids: " + ", ".join(sorted(map(str, unknown))))
        self.cases = [c for c in suite["cases"] if wanted is None or c["id"] in wanted]

    def _folder(self, case_id: str) -> Path:
        checked_identifier(case_id, "case id")
        folder = self.root / case_id
        if folder.is_symlink() or folder.resolve().parent != self.root.resolve():
            raise ValueError(f"checkpoint for {case_id} would leave {self.root}")
        return folder

    def _bound(self, case: Mapping[str, Any] | str) -> Mapping[str, Any]:
        """The pinned case a caller names; a substituted request is refused."""
        case_id = case if isinstance(case, str) else case.get("id")
        checked_identifier(case_id, "case id")
        pinned = self._pinned.get(case_id)  # type: ignore[arg-type]
        if pinned is None:
            raise ValueError(f"case {case_id} is not declared by the suite")
        if not isinstance(case, str) and "request" in case and case["request"] != pinned["request"]:
            raise ValueError(f"case {case_id} request differs from the suite's pinned request")
        return pinned

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

    def _load_receipt(self, folder: Path, body: bytes) -> HTTPReceipt | None:
        saved = folder / "receipt.json"
        if not saved.exists():
            return None
        r = json.loads(saved.read_text(encoding="utf-8"))
        if r["request_sha256"] != sha256_bytes(body):
            raise ValueError(f"checkpoint {folder} was made with a different request")
        return HTTPReceipt(
            method=r["method"], url=r["url"], request_body=body, status=r["status"],
            response_body=r["response_body"].encode("utf-8"), content_type=r["content_type"],
            elapsed_s=r["elapsed_s"], error=r["error"], response_headers=r["response_headers"],
        )

    def _save_receipt(self, folder: Path, body: bytes, receipt: HTTPReceipt, extra: Mapping[str, Any]) -> None:
        _write(folder / "receipt.json", {
            "method": receipt.method, "url": receipt.url, "request_sha256": sha256_bytes(body),
            "status": receipt.status, "content_type": receipt.content_type,
            "response_body": receipt.response_body.decode("utf-8", errors="replace"),
            "response_headers": receipt.response_headers, "elapsed_s": receipt.elapsed_s,
            "error": receipt.error, **extra, "finished_utc": utc_now(),
        })

    def _claim(self, folder: Path, body: bytes) -> bool:
        """Create the dispatch marker exclusively; False when another dispatch already holds it."""
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / "dispatch.json"
        try:
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump({"request_sha256": sha256_bytes(body), "started_utc": utc_now(),
                       "pid": os.getpid()}, out)
            out.flush()
            os.fsync(out.fileno())
        return True

    def _state(self, case_id: str) -> str:
        folder = self._folder(case_id)
        if (folder / "receipt.json").exists():
            return "complete"
        if (folder / "abandoned.json").exists():
            return "abandoned"
        if (folder / "dispatch.json").exists():
            return "unknown"
        return "unsent"

    def pending(self) -> list[str]:
        """Selected cases whose dispatch outcome is unknown (marker without receipt, not abandoned)."""
        return [c["id"] for c in self.cases if self._state(c["id"]) == "unknown"]

    def adopt(self, case_id: str, *, status: int | None, response_body: bytes, note: str) -> None:
        """Resolve an unknown dispatch with a response recovered from another record (node log, proxy).

        The adopted receipt is marked as such; nothing is sent.
        """
        case = self._bound(case_id)
        folder = self._folder(case_id)
        if self._state(case_id) != "unknown":
            raise ValueError(f"case {case_id} has no unresolved dispatch")
        if not note.strip():
            raise ValueError("adoption needs a note saying where the response came from")
        body = self._serialize(case["request"])
        receipt = HTTPReceipt("POST", "adopted", body, status, response_body)
        self._save_receipt(folder, body, receipt, {"adopted": True, "adoption_note": note})

    def abandon(self, case_id: str, *, reason: str) -> None:
        """Record an unknown dispatch as permanently unknown; it is never resent in this run."""
        self._bound(case_id)
        folder = self._folder(case_id)
        if self._state(case_id) != "unknown":
            raise ValueError(f"case {case_id} has no unresolved dispatch")
        if not reason.strip():
            raise ValueError("abandoning needs a reason")
        _write(folder / "abandoned.json", {"reason": reason, "recorded_utc": utc_now()})

    def _unknown_row(self, case: Mapping[str, Any], folder: Path, body: bytes) -> dict[str, Any]:
        reason = json.loads((folder / "abandoned.json").read_text(encoding="utf-8"))["reason"]
        return {
            "case_id": case["id"], "request": case["request"], "http_status": None,
            "error": "dispatch outcome unknown: " + reason, "response_text": None,
            "session_id": None, "session_ids": [],
            "grades": {name: {"passed": None} for name in self._grade_names},
            "metrics": None,
            "evidence": {"dispatch_state": "unknown", "request_bytes_sha256": sha256_bytes(body)},
        }

    def run_case(self, case: Mapping[str, Any] | str) -> dict[str, Any] | None:
        """Send (or resume) one declared case and return its run-record case entry.

        Returns ``None`` for a case whose dispatch outcome is unknown; it is
        not sent again.
        """
        case = self._bound(case)
        folder = self._folder(case["id"])
        body = self._serialize(case["request"])
        state = self._state(case["id"])
        if state == "abandoned":
            return self._unknown_row(case, folder, body)
        receipt = self._load_receipt(folder, body)
        if receipt is None:
            if state == "unknown" or not self._claim(folder, body):
                return None
            (folder / "request.json").write_bytes(body)
            started = utc_now()
            receipt = self._send(body)
            self._save_receipt(folder, body, receipt, {"started_utc": started})
        doc = receipt.json()
        raw, finish, completion_id = completion_content(doc)
        session = nbot_session_from_completion(completion_id)
        verified = bool(session and self._verify and self._verify(session))
        grades = self._grade(case, receipt)
        _write(folder / "grade.json", grades)
        error = receipt.error
        if error is None and not receipt.ok:
            error = f"HTTP {receipt.status}"
        saved = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        evidence = {
            "completion_id": completion_id,
            "finish_reason": finish,
            "session_verified": verified,
            "request_bytes_sha256": sha256_bytes(receipt.request_body),
            "response_bytes_sha256": sha256_bytes(receipt.response_body),
        }
        if saved.get("adopted"):
            evidence.update(dispatch_state="adopted", adoption_note=saved.get("adoption_note"))
        return {
            "case_id": case["id"],
            "request": case["request"],
            "http_status": receipt.status,
            "error": error,
            "response_text": visible_text(raw),
            "session_id": session if verified else None,
            "session_ids": [session] if verified else [],
            "grades": grades,
            "metrics": {"request_elapsed_s": round(receipt.elapsed_s, 6) if not saved.get("adopted") else None,
                        "usage": _usage(doc)},
            "evidence": evidence,
        }

    def run(
        self, *, statement: str, provenance: Mapping[str, Any] | None = None,
        on_case: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Run every selected case in suite order and return the ``new_run`` record.

        Raises :class:`UnresolvedDispatch` when any case's dispatch outcome is
        unknown; the other cases are still sent and checkpointed first.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifest()
        started = time.monotonic()
        rows, unresolved = [], []
        for case in self.cases:
            row = self.run_case(case["id"])
            if row is None:
                unresolved.append(case["id"])
                continue
            rows.append(row)
            if on_case:
                on_case(row)
        if unresolved:
            raise UnresolvedDispatch(unresolved)
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
