"""Proof detection, the secret gate, and where a validation result is allowed to land."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.evidence import (
    MAX_EVIDENCE_FILE_BYTES,
    SecretFinding,
    _decode_evidence_text,
    describe_scan_findings,
    detect_proof,
    evidence_hash,
    new_run_id,
    proof_location,
    scan_evidence,
    scan_kinds,
    store_result,
)
from quest_app.pipeline import load_world
from quest_app.view_models import build_proof_views

EVIDENCE = "participant/evidence/base-camp-repository-safety/base-camp-attempt-001"
LEAKED = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow


@pytest.fixture
def world(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    loaded = load_world(config, report)
    assert loaded is not None, report.to_text()
    return loaded


class TestProofDetection:
    def test_a_validator_requirement_is_validated_only_by_a_qualifying_result(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        results = world.participant.results_for(attempt)

        states = detect_proof(quest, config, attempt.evidence_path, results)

        validator_items = [item for item in quest.proof if item.type == "validator"]
        for item in validator_items:
            matching = [r for r in results if r.validator_id == item.validator]
            expected_validated = any(r.qualifies for r in matching)
            assert (states[item.id] == "validated") is expected_validated

    def test_detection_never_claims_validated_without_a_result(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        quest = world.content.quests["playwright-first-independent-test"]
        states = detect_proof(quest, config, None, ())
        assert "validated" not in states.values()

    def test_a_demonstration_cannot_be_detected_from_the_filesystem(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """A checkbox must not stand in for a person watching someone work."""
        for quest in world.content.quests.values():
            states = detect_proof(quest, config, None, ())
            for item in quest.proof:
                if item.type in ("demonstration", "review"):
                    assert states[item.id] == "missing"

    def test_evidence_saved_where_the_quest_says_to_save_it_is_detected(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The quest names `attempt-001/logs/…`; the real package is `<prefix>-attempt-001`.

        Every file-proof path in the curriculum points into `logs/` or `screenshots/`, the
        subdirectories the evidence package is created with, and the authored attempt
        directory is one no attempt ever has. Detection looked for the bare filename at the
        top of the package, so following the instructions produced "Not detected".
        """
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")
        assert "/attempt-001/logs/" in item.path, "this test is about that shape of path"

        package = config.resolve_participant_path(attempt.evidence_path)
        saved = package / "logs" / Path(item.path).name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text("second run created no duplicate\n")

        states = detect_proof(quest, config, attempt.evidence_path, ())
        assert states[item.id] == "detected"

    def test_the_package_fallback_keeps_the_subdirectory_the_quest_asked_for(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Accepting the file anywhere under the package would be a weaker rule, not a fix."""
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")

        package = config.resolve_participant_path(attempt.evidence_path)
        wrong = package / "screenshots" / Path(item.path).name
        wrong.parent.mkdir(parents=True, exist_ok=True)
        wrong.write_text("saved in the wrong place\n")

        states = detect_proof(quest, config, attempt.evidence_path, ())
        assert states[item.id] == "missing"

    def test_a_file_at_the_literal_authored_attempt_path_is_not_detected(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Round 17 L1: the literal `attempt-001/` folder is outside the real package, so
        nothing scans or fingerprints it. Counting it as detected let an unscanned file carry
        a submission and change after approval unseen."""
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")

        literal = config.resolve_participant_path(item.path)
        literal.parent.mkdir(parents=True, exist_ok=True)
        literal.write_text(f"token={LEAKED}\n")

        assert detect_proof(quest, config, attempt.evidence_path, ())[item.id] == "missing"

    def test_proof_rows_show_the_path_inside_the_real_package(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Round 17 L2: pages pointed participants and reviewers at `attempt-001/`."""
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")

        shown = proof_location(item.path, attempt.evidence_path)
        assert shown == f"{attempt.evidence_path}/logs/{Path(item.path).name}"
        required, _ = build_proof_views(quest, None, attempt.evidence_path)
        assert shown in [view.path for view in required]
        # Without an attempt, and for a path outside the quest's own area, it is as authored.
        assert proof_location(item.path, None) == item.path
        assert proof_location("participant/context/x.md", attempt.evidence_path) == (
            "participant/context/x.md"
        )

    def test_a_traversing_proof_path_is_never_detected(self, world, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        import dataclasses

        quest = world.content.quests["base-camp-repository-safety"]
        item = dataclasses.replace(quest.proof[0], type="file", path="../../../etc/passwd")
        hostile = dataclasses.replace(quest, proof=(item,))
        assert detect_proof(hostile, config, None, ())[item.id] == "missing"

    def test_an_empty_declared_directory_is_not_detected(self, world, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        """Round 15 T4: `target.is_dir() and any(target.iterdir())` is what tells an empty
        directory from a populated one. Removing the `any(...)` half passed the entire
        997-test non-UI suite with zero failures — a participant who created the required
        directory but never put anything in it would be shown "detected" rather than
        "missing"."""
        import dataclasses

        quest = world.content.quests["base-camp-repository-safety"]
        directory_path = "participant/context/round15-t4-empty-dir"
        config.resolve_participant_path(directory_path).mkdir(parents=True, exist_ok=True)
        item = dataclasses.replace(quest.proof[0], type="directory", path=directory_path)
        hostile = dataclasses.replace(quest, proof=(item,))

        assert detect_proof(hostile, config, None, ())[item.id] == "missing"

    def test_an_environment_failure_result_is_a_warning_not_missing(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Round 15 T6: the `("inconclusive", "environment_failure")` tuple in `_detect_one`
        had no test naming `environment_failure` specifically. Dropping it from the tuple
        passed every test file that references `environment_failure` or the proof/validator
        views, with zero failures."""
        from quest_app.progress import ValidationResult

        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "validator")
        result = ValidationResult(
            run_id="round15-t6-run",
            validator_id=item.validator,
            validator_version=1,
            quest_id=quest.id,
            attempt_id=attempt.attempt_id,
            started_at="2026-09-16T10:00:00Z",
            completed_at="2026-09-16T10:00:01Z",
            duration_ms=500,
            outcome="environment_failure",
            checks=(),
            redaction_applied=False,
            source="participant/evidence/x/y/validation/round15-t6-run.json",
        )

        states = detect_proof(quest, config, attempt.evidence_path, (result,))
        assert states[item.id] == "warning"


class TestSecretScanning:
    def test_clean_evidence_produces_no_findings(self, config: AppConfig) -> None:
        assert scan_evidence(config, EVIDENCE) == []

    def test_a_planted_credential_is_found(self, config: AppConfig) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"I used token={LEAKED} to authenticate.\n")
        findings = scan_evidence(config, EVIDENCE)
        assert findings
        assert findings[0].path.endswith("notes.md")

    def test_a_finding_never_carries_the_value(self, config: AppConfig) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"token={LEAKED}\n")
        # SecretFinding is slotted, so `asdict` rather than `__dict__`.
        import dataclasses

        rendered = json.dumps([dataclasses.asdict(f) for f in scan_evidence(config, EVIDENCE)])
        assert LEAKED not in rendered

    def test_an_allow_pragma_in_evidence_does_not_switch_the_scan_off(
        self, config: AppConfig
    ) -> None:
        """The pragma is a repository-hygiene device, not something a submission can use."""
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"token={LEAKED}  # secret-scan: allow\n")
        assert scan_evidence(config, EVIDENCE), "evidence scanning must ignore the pragma"

    def test_a_byte_that_is_not_utf8_does_not_hide_the_file(self, config: AppConfig) -> None:
        """One Latin-1 byte made the whole file undecodable, and the scan skipped it."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "run.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"Caf\xe9 opened\n" + f"token={LEAKED}\n".encode())
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["run.log"]

    def test_a_file_that_cannot_be_read_blocks_rather_than_passing(self, config: AppConfig) -> None:
        if os.geteuid() == 0:
            pytest.skip("root can read a file whatever its mode")
        target = config.resolve_participant_path(EVIDENCE) / "unreadable.md"
        target.write_text("anything\n")
        target.chmod(0)
        try:
            findings = scan_evidence(config, EVIDENCE)
        finally:
            target.chmod(0o600)
        assert [finding.description for finding in findings] == ["could not be read to check it"]
        # Round 17: and it is not worded as a secret to the participant or the reviewer.
        assert scan_kinds(findings) == frozenset({"unreadable"})
        (problem,) = describe_scan_findings(findings)
        assert "secret" not in problem and "could not be read" in problem

    def test_a_traversing_evidence_path_scans_nothing(self, config: AppConfig) -> None:
        assert scan_evidence(config, "participant/evidence/../../etc") == []

    # Round 16 E12: the skip list used to go by extension alone, so a plain-text secret
    # saved under a name claiming to be one of these formats passed the scan clean and
    # `mark-evidence-ready` waved the package through.
    def test_a_plaintext_secret_saved_with_a_pdf_extension_is_still_found(
        self, config: AppConfig
    ) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "terminal.pdf"
        target.write_text(f"export GITHUB_TOKEN={LEAKED}\n")
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["terminal.pdf"]

    def test_a_plaintext_secret_saved_with_a_zip_extension_is_still_found(
        self, config: AppConfig
    ) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "env-backup.zip"
        target.write_text(f"token={LEAKED}\n")
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["env-backup.zip"]

    @pytest.mark.parametrize(
        ("name", "header"),
        [
            ("screenshot.txt", b"\x89PNG\r\n\x1a\n"),
            ("notes.txt", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"),
            ("archive.log", b"PK\x03\x04"),
            ("photo.md", b"\xff\xd8\xff"),
            ("frame.dat", b"GIF89a\x01\x00\x01\x00\x80\x00\x00"),
            ("image.out", b"RIFF\x00\x00\x00\x00WEBP"),
        ],
    )
    def test_a_real_binary_format_is_skipped_by_content_whatever_its_name(
        self, config: AppConfig, name: str, header: bytes
    ) -> None:
        target = config.resolve_participant_path(EVIDENCE) / name
        target.write_bytes(header + f"token={LEAKED}".encode())
        assert scan_evidence(config, EVIDENCE) == []

    # Round 17 E7: GIF and PDF signatures are plain ASCII, so a text file could open with
    # one and be skipped unread.
    @pytest.mark.parametrize("header", [b"GIF89a\n", b"GIF87a\n", b"%PDF-1.4\n"])
    def test_a_text_file_opening_with_an_ascii_signature_is_still_scanned(
        self, config: AppConfig, header: bytes
    ) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "capture.gif"
        target.write_bytes(header + f"GITHUB_TOKEN={LEAKED}\n".encode())
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["capture.gif"]

    def test_two_different_short_secrets_in_one_file_are_both_reported(
        self, config: AppConfig
    ) -> None:
        """Round 17 E8: findings were deduplicated by excerpt, which for a value under 12
        characters is only its length, so the second secret was never shown."""
        target = config.resolve_participant_path(EVIDENCE) / "two.env"
        target.write_text(
            "password=Abcdefgh12\n"  # secret-scan: allow
            "password=Zyxwvuts98\n"  # secret-scan: allow
        )
        findings = scan_evidence(config, EVIDENCE)
        assert sorted(finding.line for finding in findings) == [1, 2]

    def test_an_oversize_real_image_is_skipped_rather_than_flagged_oversize(
        self, config: AppConfig
    ) -> None:
        """The skip decision reads only the header, so a legitimate multi-megabyte
        screenshot is still skipped whatever its size, rather than reading the whole file
        first and then reporting it too large to check."""
        target = config.resolve_participant_path(EVIDENCE) / "big.png"
        target.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_EVIDENCE_FILE_BYTES + 1000))
        assert scan_evidence(config, EVIDENCE) == []

    def test_the_full_file_scan_path_stays_fast_on_a_two_megabyte_adversarial_file(
        self, config: AppConfig
    ) -> None:
        """Round 16 E1/E2, through the real call path a build and `mark-evidence-ready`
        use rather than the bare regex or `scan_text` in isolation: `scan_evidence` decodes
        every candidate encoding (round 15 E6) and runs the full pattern set over each one.
        A single NUL byte is enough to add the NUL-stripped candidate alongside the plain
        UTF-8 one, so this exercises decoding as well as matching. A generous absolute
        bound is used rather than a tight one, since this is one combined path rather than
        an isolated regex and a slow CI runner should not flake it (round 16's own audit
        found a 5-second bound fail on GitHub runners for a related test)."""
        target = config.resolve_participant_path(EVIDENCE) / "adversarial.log"
        unit = "sk-"
        body = unit * (MAX_EVIDENCE_FILE_BYTES // len(unit))
        raw = body.encode()[: MAX_EVIDENCE_FILE_BYTES - 1] + b"\x00"
        target.write_bytes(raw)
        started = time.monotonic()
        findings = scan_evidence(config, EVIDENCE)
        elapsed = time.monotonic() - started
        assert elapsed < 20, f"a 2 MB adversarial evidence file took {elapsed:.1f}s to scan"
        assert findings == []

    def test_a_utf16_file_does_not_hide_the_token(self, config: AppConfig) -> None:
        """Round 14 E7: a PowerShell `>` redirection writes UTF-16LE by default. Decoded as
        UTF-8 with replacement, every other byte becomes U+FFFD and the token vanished."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "transcript.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"connected\r\ntoken={LEAKED}\r\n".encode("utf-16"))
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["transcript.txt"]

    def test_a_bom_less_utf16le_file_does_not_hide_the_token(self, config: AppConfig) -> None:
        """Round 15 T3: without a byte-order mark, `_decode_evidence_text` guesses
        endianness from which byte position of each pair carries more NUL bytes. The only
        UTF-16 regression test before this one always writes with `.encode("utf-16")`, which
        always emits a BOM, so a backwards guess in that heuristic branch never showed up in
        the suite (it would byte-swap real text into garbage no pattern matches)."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "le-no-bom.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = f"connected\r\ntoken={LEAKED}\r\n".encode("utf-16-le")
        assert not raw.startswith((b"\xff\xfe", b"\xfe\xff")), "this test needs no BOM"
        target.write_bytes(raw)
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["le-no-bom.txt"]

    def test_a_bom_less_utf16be_file_does_not_hide_the_token(self, config: AppConfig) -> None:
        """Round 15 T3: the big-endian half of the same heuristic."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "be-no-bom.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = f"connected\r\ntoken={LEAKED}\r\n".encode("utf-16-be")
        assert not raw.startswith((b"\xff\xfe", b"\xfe\xff")), "this test needs no BOM"
        target.write_bytes(raw)
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["be-no-bom.txt"]

    @pytest.mark.parametrize("codec", ["utf-16-le", "utf-16-be"])
    def test_the_bom_less_endianness_guess_reads_multibyte_text_correctly(self, codec: str) -> None:
        """Round 15 T3, isolated from the fallback candidates: an ASCII-only token, like the
        two tests above use, is reconstructed by the NUL-stripped candidate regardless of
        which endianness the heuristic guesses, so those two tests alone would not catch the
        heuristic's ternary getting flipped (round 14's mutation-testing round found exactly
        that: swapping it passed every other test in this file). A non-ASCII character does
        not survive NUL-stripping intact, and comes out as a different character entirely
        under the wrong endianness, so it is what actually proves the guess itself is right."""
        text = "connected: café ok\r\n" * 20
        raw = text.encode(codec)
        assert not raw.startswith((b"\xff\xfe", b"\xfe\xff")), "this test needs no BOM"
        assert raw.count(b"\0") / len(raw) > 0.3, "this test needs the heuristic branch"
        assert any("café" in candidate for candidate in _decode_evidence_text(raw))

    def test_a_utf8_file_with_an_appended_utf16_tail_does_not_hide_the_token(
        self, config: AppConfig
    ) -> None:
        """Round 15 E6: PowerShell 5.1's `>>` append writes UTF-16LE onto a file a previous
        run already created in UTF-8. A single whole-file decoding guess cannot read both
        halves correctly, and the large UTF-8 head dilutes the NUL ratio well under the
        heuristic's 30% trigger, so the file was decoded as UTF-8 and the tail became
        replacement characters — invisible to every pattern."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "mixed-encoding.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        utf8_head = ("Run 1 output: synchronized 42 cards, nothing changed.\n" * 200).encode()
        utf16_tail = f"PS> gh auth token >> run.log\r\ntoken={LEAKED}\r\n".encode("utf-16-le")
        raw = utf8_head + utf16_tail
        assert raw.count(b"\0") / len(raw) < 0.3, "this test needs a ratio under the old trigger"
        target.write_bytes(raw)
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["mixed-encoding.txt"]

    def test_bom_less_utf16_cjk_text_does_not_hide_the_token(self, config: AppConfig) -> None:
        """Round 15 E6: a wide CJK character fills both bytes of its UTF-16 pair and
        contributes no NUL of its own, so a file that is genuinely UTF-16 throughout can
        still dilute the whole-file NUL ratio under the 30% trigger."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "cjk.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        text = "同步完成。卡片已更新。" * 300 + f"token={LEAKED}"
        raw = text.encode("utf-16-le")
        assert raw.count(b"\0") / len(raw) < 0.3, "this test needs a ratio under the old trigger"
        target.write_bytes(raw)
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["cjk.txt"]

    def test_a_bom_marked_utf32_file_does_not_hide_the_token(self, config: AppConfig) -> None:
        """Round 15 E6: a UTF-32 byte-order mark starts with the same two bytes as a
        UTF-16LE one (`\\xff\\xfe`), so it must be checked before the UTF-16 checks or a
        UTF-32 file is silently misread as UTF-16 and every character comes out wrong."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "utf32.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(("﻿" + f"token={LEAKED}").encode("utf-32"))
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["utf32.txt"]

    def test_utf32_bom_decodes_correctly_rather_than_as_utf16(self) -> None:
        """Round 15 E6, isolated from the fallback candidates: `scan_evidence` still finds a
        lone ASCII token in a misread UTF-32 file because the NUL-stripped candidate happens
        to reconstruct any single-byte-per-character run regardless of format, which would
        mask a regression in the BOM check order. A multi-byte character does not survive
        that fallback, so it is what actually proves the UTF-32 branch fired: misread as
        UTF-16, every character comes out followed by a stray NUL character (`c\\x00a\\x00
        f\\x00é\\x00`), and NUL-stripping a multi-byte character garbles it too."""
        raw = ("﻿café").encode("utf-32")
        assert any("café" in candidate for candidate in _decode_evidence_text(raw))

    def test_a_path_swapped_for_a_fifo_does_not_hang_the_header_read(
        self, config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Round 17 A-E13: the header read was a plain `open("rb")` after `is_file()`, so a
        path swapped for a FIFO between the two blocked the scan forever under the store,
        generated and service locks. `is_file` is made to answer for the file that was
        there a moment ago, which is exactly what the race leaves the scan believing; the
        scan runs in a thread so a regression fails on the timeout instead of hanging."""
        import threading
        from pathlib import Path as RealPath

        target = config.resolve_participant_path(EVIDENCE) / "logs" / "swapped.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        os.mkfifo(target)
        real_is_file = RealPath.is_file
        monkeypatch.setattr(
            RealPath, "is_file", lambda self: self.name == "swapped.log" or real_is_file(self)
        )
        outcome: list[list[SecretFinding]] = []
        worker = threading.Thread(
            target=lambda: outcome.append(list(scan_evidence(config, EVIDENCE))), daemon=True
        )
        worker.start()
        worker.join(timeout=10)
        if worker.is_alive():
            # Unblock the stuck reader so the thread does not outlive the test.
            with target.open("wb"):
                pass
            worker.join(timeout=10)
            pytest.fail("the secret scan blocked opening a FIFO")
        (findings,) = outcome
        assert [(f.path.rsplit("/", 1)[-1], f.description) for f in findings] == [
            ("swapped.log", "could not be read to check it")
        ]

    def test_an_unreadable_directory_blocks_rather_than_passing(self, config: AppConfig) -> None:
        """Round 14 E5: `rglob` silently drops a directory it cannot list instead of raising,
        so a token behind one used to pass with `secret_scan_clean: true`."""
        if os.geteuid() == 0:
            pytest.skip("root can read a directory whatever its mode")
        private = config.resolve_participant_path(EVIDENCE) / "logs" / "private"
        private.mkdir(parents=True, exist_ok=True)
        (private / "leak.md").write_text(f"token={LEAKED}\n")
        private.chmod(0)
        try:
            findings = scan_evidence(config, EVIDENCE)
        finally:
            private.chmod(0o700)
        assert [finding.description for finding in findings] == ["could not be read to check it"]
        assert findings[0].path.endswith("logs/private")


class TestEvidenceHash:
    def test_the_hash_changes_when_the_evidence_changes(self, config: AppConfig) -> None:
        before = evidence_hash(config, EVIDENCE)
        (config.resolve_participant_path(EVIDENCE) / "PROOF.md").write_text("# Different\n")
        assert evidence_hash(config, EVIDENCE) != before

    def test_a_new_validation_run_does_not_change_the_hash(self, config: AppConfig) -> None:
        """Otherwise re-running a check would make every prior review look stale."""
        before = evidence_hash(config, EVIDENCE)
        store_result(
            config,
            EVIDENCE,
            {
                "schema_version": 1,
                "run_id": new_run_id("validate-repository-foundation"),
                "validator_id": "validate-repository-foundation",
                "validator_version": 1,
                "quest_id": "base-camp-repository-safety",
                "attempt_id": "base-camp-attempt-001",
                "started_at": "2026-09-16T10:00:00Z",
                "completed_at": "2026-09-16T10:00:01Z",
                "duration_ms": 1000,
                "outcome": "pass",
                "checks": [{"id": "c", "outcome": "pass", "summary": "ok"}],
                "redaction_applied": False,
            },
        )
        assert evidence_hash(config, EVIDENCE) == before

    def test_a_missing_directory_has_no_hash(self, config: AppConfig) -> None:
        assert evidence_hash(config, "participant/evidence/nothing/here") is None

    def test_an_unreadable_file_is_named_relatively_not_by_a_traceback(
        self, config: AppConfig
    ) -> None:
        """Round 13 E8.

        An unreadable file used to crash the hash outright with an unhandled `OSError`, and
        the traceback that reached the terminal carried this file's absolute path. It must
        instead be reported through `UnreadableFileError`, naming the file by a path relative
        to the evidence package.
        """
        from quest_app.hashing import UnreadableFileError

        if os.geteuid() == 0:
            pytest.skip("root can read a file whatever its mode")
        target = config.resolve_participant_path(EVIDENCE) / "unreadable.md"
        target.write_text("anything\n")
        target.chmod(0)
        try:
            with pytest.raises(UnreadableFileError) as raised:
                evidence_hash(config, EVIDENCE)
        finally:
            target.chmod(0o600)
        assert raised.value.relative_path == "unreadable.md"
        assert str(config.repo_root) not in str(raised.value)
        assert str(config.participant_root) not in str(raised.value)

    def test_an_unreadable_directory_raises_the_same_error_the_file_case_does(
        self, config: AppConfig
    ) -> None:
        """Round 14 E5: `rglob` silently drops a directory it cannot list, so the hash used
        to stay stable across a change nobody could see (round 13 E8 covered only files)."""
        from quest_app.hashing import UnreadableFileError

        if os.geteuid() == 0:
            pytest.skip("root can read a directory whatever its mode")
        private = config.resolve_participant_path(EVIDENCE) / "logs" / "private"
        private.mkdir(parents=True, exist_ok=True)
        (private / "leak.md").write_text("anything\n")
        private.chmod(0)
        try:
            with pytest.raises(UnreadableFileError) as raised:
                evidence_hash(config, EVIDENCE)
        finally:
            private.chmod(0o700)
        assert raised.value.relative_path == "logs/private"
        assert str(config.repo_root) not in str(raised.value)
        assert str(config.participant_root) not in str(raised.value)


def test_a_result_is_stored_by_its_attempt_not_by_its_own_claim(config: AppConfig) -> None:
    """The path comes from the attempt, so a record cannot file itself elsewhere."""
    stored = store_result(
        config,
        EVIDENCE,
        {
            "run_id": "probe-run",
            "attempt_id": "some-other-attempt",
            "quest_id": "jira-read-assigned-stories",
        },
    )
    assert stored.startswith(EVIDENCE)
    assert (config.resolve_participant_path(EVIDENCE) / "validation" / "probe-run.json").exists()


def test_run_ids_do_not_collide() -> None:
    assert len({new_run_id("v") for _ in range(50)}) == 50


def test_a_stored_result_path_is_participant_relative(config: AppConfig, tmp_path: Path) -> None:
    del tmp_path
    stored = store_result(config, EVIDENCE, {"run_id": "r1"})
    assert stored.startswith("participant/")
    assert not Path(stored).is_absolute()


@pytest.mark.parametrize(
    ("outcome", "counts"),
    [
        ("pass", True),
        ("warning", True),
        ("fail", False),
        ("inconclusive", False),
        ("interrupted", False),
        ("environment_failure", False),
    ],
)
def test_only_a_pass_or_a_warning_counts_towards_local_validation(
    outcome: str, counts: bool
) -> None:
    """`qualifies` is the gate for `locally_validated`, and it survived being widened.

    Adding `inconclusive` and `interrupted` to it passed the whole suite: the one test that
    touched it computed its expectation from the same property. "We could not tell" is not
    evidence, and a run that was stopped is not a run.
    """
    from quest_app.progress import ValidationResult

    result = ValidationResult(
        run_id="run-001",
        validator_id="validate-repository-foundation",
        validator_version=1,
        quest_id="base-camp-repository-safety",
        attempt_id="base-camp-attempt-001",
        started_at="2026-09-22T00:00:00+00:00",
        completed_at="2026-09-22T00:00:01+00:00",
        duration_ms=1000,
        outcome=outcome,
        checks=(),
        redaction_applied=False,
        source="participant/evidence/x/y/validation/run-001.json",
    )
    assert result.qualifies is counts
