"""Sign PEP 740 attestations for the dist files about to be uploaded (workspace H33 U8).

Run ONLY in `.github/workflows/publish.yml`'s `publish` job, inside its own venv with the pinned
`pypi-attestations` (and its `sigstore`), fetched by the checked commit like every script there.
It mirrors pypa/gh-action-pypi-publish's attestations.py (v1.14.3): the identity is the job's
ambient GitHub OIDC credential (audience `sigstore`, `id-token: write`), signed against Sigstore's
production trust config, one `<dist>.publish.attestation` beside each dist, which `twine upload
--attestations` sends. Unlike `pypi-attestations sign`, it NEVER falls back to an interactive
OAuth flow: no ambient credential = exit 1 (a CI job must fail, not wait for a browser).

Usage: python pypi_attest.py <dist-file>...
  stdout: twine's argument list — each dist, then its attestation (one path per line)
  stderr: progress
Exit 0 = every file signed; 1 = refused (no credential, a pre-existing attestation, no file).
"""
from __future__ import annotations

import sys
from pathlib import Path


def attestation_path(dist: Path) -> Path:
    """`x.whl` -> `x.whl.publish.attestation` (the name twine --attestations looks for)."""
    return dist.with_name(dist.name + ".publish.attestation")


def plan(files: list[str]) -> list[tuple[Path, Path]]:
    """(dist, attestation) pairs; ValueError for a missing dist or a pre-existing attestation."""
    if not files:
        raise ValueError("no dist files given")
    pairs: list[tuple[Path, Path]] = []
    for name in files:
        dist = Path(name)
        if not dist.is_file():
            raise ValueError(f"{dist} is not a file")
        att = attestation_path(dist)
        if att.exists():
            raise ValueError(f"{att} already exists — refusing to overwrite an attestation")
        pairs.append((dist, att))
    return pairs


def main(argv: list[str]) -> int:
    try:
        pairs = plan(argv)
    except ValueError as e:
        print(f"pypi_attest: refused: {e}", file=sys.stderr)
        return 1
    # Third-party imports here only: the publish job's venv has them; the gate and the tests
    # import this module without them.
    from pypi_attestations import Attestation, Distribution  # type: ignore[import-not-found]
    from sigstore.models import ClientTrustConfig  # type: ignore[import-not-found]
    from sigstore.oidc import IdentityToken, detect_credential  # type: ignore[import-not-found]
    from sigstore.sign import SigningContext  # type: ignore[import-not-found]

    credential = detect_credential()  # audience is always `sigstore`
    if not credential:
        print("pypi_attest: refused: no ambient OIDC credential (needs `id-token: write` in a "
              "GitHub Actions job); never an interactive flow", file=sys.stderr)
        return 1
    identity = IdentityToken(credential)
    context = SigningContext.from_trust_config(ClientTrustConfig.production())
    with context.signer(identity, cache=True) as signer:
        for dist, att in pairs:
            attestation = Attestation.sign(signer, Distribution.from_file(dist))
            att.write_text(attestation.model_dump_json(), encoding="utf-8")
            print(f"pypi_attest: signed {dist.name} -> {att.name}", file=sys.stderr, flush=True)
    # stdout = twine's argument list: each dist FOLLOWED BY its attestation. twine does not look
    # for attestations beside the dists — it sorts the files it is GIVEN (measured 2026-11-10:
    # given only the dists, `twine upload --attestations` fails "Upload with attestations
    # requested, but … has no associated attestations" — 2.0.4's failed publish).
    for line in upload_args(pairs):
        print(line)
    return 0


def upload_args(pairs: list[tuple[Path, Path]]) -> list[str]:
    """`twine upload --attestations` arguments: every dist, then its attestation."""
    return [str(p) for dist, att in pairs for p in (dist, att)]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
