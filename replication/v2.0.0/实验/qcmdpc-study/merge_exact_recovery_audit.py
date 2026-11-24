"""Merge independently completed exact-recovery audit groups.

The formal audit can be split across processes because each group is
independent.  This helper validates the split outputs and their producing
manifests before copying records into the formal directory and regenerating
the count-preserving overall summary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import exact_recovery_audit as audit


EXPECTED_GROUPS = tuple(audit.GROUPS)
# The formal archive contains byte-compatible reporting revisions.  The
# decoder, key pool, error stream, and per-trial accounting are unchanged;
# only aggregate reporting and the default output directory changed.
COMPATIBLE_SCRIPT_HASHES = {
    "0c8264e16f4828309a5d771e06a53c8c12962af89d9ade0e66f2e26ed1d8a3af",
    "01c2c8ac425cabe383590ccff8ab0a1fe349e0086dc1b2eceff524605c98cbbe",
    "52edbacdc4b32f7cdcbafc0b4a0e5c90c0de335ea713dc674c30c78994a55eab",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_group(gid: str, row: dict, manifest: dict) -> None:
    if row.get("gid") != gid:
        raise ValueError(f"{gid}: group id mismatch")
    if row.get("parameter") != audit.PARAM:
        raise ValueError(f"{gid}: parameter mismatch")
    if row.get("seed") != audit.SEED or manifest.get("seed") != audit.SEED:
        raise ValueError(f"{gid}: seed mismatch")
    if manifest.get("parameter") != audit.PARAM or manifest.get("arms") != list(audit.ARMS):
        raise ValueError(f"{gid}: producing manifest parameter or arms mismatch")
    if manifest.get("formal_fresh_from") != {
        name: spec["fresh_from"] for name, spec in audit.GROUPS.items()
    }:
        raise ValueError(f"{gid}: fresh-key boundary mismatch")
    expected_keys = len(audit.KeyPool(audit.SEED, audit.PARAM, gid, audit.GROUPS[gid]["spec"]).keys) - audit.GROUPS[gid]["fresh_from"]
    if row.get("n_keys") != expected_keys or row.get("errors_per_key") != audit.FULL_ERRORS:
        raise ValueError(
            f"{gid}: expected {expected_keys} keys x {audit.FULL_ERRORS} errors, "
            f"got {row.get('n_keys')} x {row.get('errors_per_key')}"
        )
    start = audit.GROUPS[gid]["fresh_from"]
    if row.get("fresh_index_range") != [start, start + expected_keys]:
        raise ValueError(f"{gid}: fresh key range mismatch")
    expected_processed = expected_keys * audit.FULL_ERRORS
    if row.get("processed") != expected_processed:
        raise ValueError(f"{gid}: processed count mismatch")
    if set(row.get("arms", {})) != set(audit.ARMS):
        raise ValueError(f"{gid}: arm set mismatch")
    for arm, values in row.get("arms", {}).items():
        if values.get("processed") != expected_processed or values.get("trials") != expected_processed:
            raise ValueError(f"{gid}/{arm}: arm trial count mismatch")
        if values.get("processed") != values.get("zero_syndrome", 0) + values.get("nonzero_syndrome", 0):
            raise ValueError(f"{gid}/{arm}: syndrome count identity failed")
        if values.get("zero_syndrome_miscorrections") != 0:
            raise ValueError(f"{gid}/{arm}: nonzero zero-syndrome miscorrections")
        if values.get("exact_recovery") != values.get("zero_syndrome"):
            raise ValueError(f"{gid}/{arm}: exact recovery differs from zero-syndrome count")
        if values.get("exact_recovery_failures") != expected_processed - values["exact_recovery"]:
            raise ValueError(f"{gid}/{arm}: exact failure count identity failed")
        per_key = row.get("per_key", {}).get(arm, [])
        if len(per_key) != expected_keys:
            raise ValueError(f"{gid}/{arm}: per-key record count mismatch")
        if [entry.get("key_index") for entry in per_key] != list(range(start, start + expected_keys)):
            raise ValueError(f"{gid}/{arm}: per-key indices mismatch")
        for field, summary_field in (
            ("zero_syndrome", "zero_syndrome"),
            ("nonzero_syndrome", "nonzero_syndrome"),
            ("zero_syndrome_miscorrection", "zero_syndrome_miscorrections"),
            ("exact_recovery", "exact_recovery"),
        ):
            if sum(entry.get(field, 0) for entry in per_key) != values[summary_field]:
                raise ValueError(f"{gid}/{arm}: per-key {field} sum mismatch")
    if manifest.get("protocol") != audit.PROTOCOL:
        raise ValueError(f"{gid}: protocol mismatch")
    script_hash = manifest.get("script_sha256")
    if script_hash not in COMPATIBLE_SCRIPT_HASHES:
        raise ValueError(f"{gid}: unsupported audit script hash {script_hash}")
    selected_groups = manifest.get("selection", {}).get("groups", [])
    if gid not in selected_groups:
        raise ValueError(f"{gid}: group is absent from the producing manifest")
    if manifest.get("selection", {}).get("errors_per_key") != audit.FULL_ERRORS:
        raise ValueError(f"{gid}: errors-per-key mismatch")
    if manifest.get("selection", {}).get("keys_per_group") is not None:
        raise ValueError(f"{gid}: pilot key selection is not a formal audit")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal", type=Path, default=audit.OUT / "formal_full")
    parser.add_argument(
        "--source",
        type=Path,
        default=audit.OUT,
        help="directory containing parallel_G2 and parallel_G3 outputs",
    )
    args = parser.parse_args()
    formal = args.formal.resolve()
    source = args.source.resolve()
    formal.mkdir(parents=True, exist_ok=True)

    manifest_path = formal / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing formal manifest: {manifest_path}")
    formal_manifest = _load(manifest_path)
    if formal_manifest.get("protocol") != audit.PROTOCOL:
        raise SystemExit("formal manifest uses a different audit protocol")
    if formal_manifest.get("script_sha256") not in COMPATIBLE_SCRIPT_HASHES:
        raise SystemExit("formal manifest uses an unsupported audit script revision")

    groups: dict[str, dict] = {}
    manifest_by_group: dict[str, dict] = {}
    missing_targets: dict[str, Path] = {}
    for gid in EXPECTED_GROUPS:
        target = formal / f"group_{gid}.json"
        if gid == "G0":
            if not target.exists():
                raise SystemExit(f"missing completed G0 group: {target}")
            manifest_for_group = formal_manifest
            row = _load(target)
        else:
            parallel_dir = source / f"parallel_{'G2' if gid == 'G2_d12' else 'G3'}"
            candidate = parallel_dir / f"group_{gid}.json"
            if not candidate.exists():
                raise SystemExit(f"missing completed group: {candidate}")
            parallel_manifest_path = parallel_dir / "manifest.json"
            if not parallel_manifest_path.exists():
                raise SystemExit(f"missing parallel manifest: {parallel_manifest_path}")
            manifest_for_group = _load(parallel_manifest_path)
            row = _load(candidate)
            if target.exists():
                if _load(target) != row:
                    raise ValueError(f"{gid}: existing formal record differs from its parallel source")
            else:
                missing_targets[gid] = target
        _check_group(gid, row, manifest_for_group)
        groups[gid] = row
        manifest_by_group[gid] = manifest_for_group

    # No output is written until all groups and provenance have passed.
    for gid, target in missing_targets.items():
        target.write_text(json.dumps(groups[gid], indent=2) + "\n", encoding="utf-8")

    script_hashes = {gid: manifest_by_group[gid]["script_sha256"] for gid in EXPECTED_GROUPS}
    mixed_revision = len(set(script_hashes.values())) > 1
    report = {
        "manifest": formal_manifest,
        "groups": groups,
        "script_hashes_by_group": script_hashes,
        "compatibility_note": (
            "Groups use byte-compatible audit reporting revisions with different "
            "script hashes; this mixed archive records the source hash by group. "
            "The decoder, sampling, and per-trial accounting are unchanged, but "
            "a single-hash rerun remains the strictest reproducibility form."
            if mixed_revision else "All groups use the same audit script hash."
        ),
    }
    report["overall"] = audit.aggregate_groups(groups)
    (formal / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Exact-recovery audit summary",
        "",
        "Protocol: `exact_recovery_audit_v1`; parameter: `P1prime`; "
        "success is reported separately as zero syndrome and exact error recovery.",
        "",
        "| Group | Arm | Processed | Zero syndrome | Exact recovery | Exact failures | Zero-syndrome miscorrections |",
        "|:--|:--|--:|--:|--:|--:|--:|",
    ]
    for gid in EXPECTED_GROUPS:
        for arm, row in groups[gid]["arms"].items():
            lines.append(
                f"| {gid} | {arm} | {row['processed']:,} | {row['zero_syndrome']:,} | "
                f"{row['exact_recovery']:,} | {row['exact_recovery_failures']:,} | "
                f"{row['zero_syndrome_miscorrections']:,} |"
            )
    lines.extend([
        "",
        "All group rows satisfy `processed = zero_syndrome + nonzero_syndrome` and "
        "`exact_recovery_failures = nonzero_syndrome + zero_syndrome_miscorrections`.",
        "No zero-syndrome miscorrections were observed in the completed formal pool.",
        "",
    ])
    (formal / "audit_summary.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {
        arm: {
            "processed": row["processed"],
            "exact_recovery_failures": row["exact_recovery_failures"],
            "zero_syndrome_miscorrections": row["zero_syndrome_miscorrections"],
        }
        for arm, row in report["overall"].items()
    }
    print(json.dumps({"output": str(formal), "groups": list(groups), "overall": summary}, indent=2))


if __name__ == "__main__":
    main()
