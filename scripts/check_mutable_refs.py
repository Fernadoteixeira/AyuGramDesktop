#!/usr/bin/env python3
"""Detect mutable git references in build scripts.

Scans build files for git clone/checkout/fetch commands that reference
mutable tags or unpinned branches instead of immutable commit SHAs.

Mutable references are a supply-chain risk: a tag or branch can be moved
by the repository owner at any time, silently changing the code that gets
built.  Pinning every dependency to a 40-hex commit SHA eliminates this.

Exit codes:
    0 — no mutable references found
    1 — one or more mutable references found
    2 — usage error

Usage:
    python scripts/check_mutable_refs.py
    python scripts/check_mutable_refs.py --allowlist allowlist.txt
    python scripts/check_mutable_refs.py --repo-root /path/to/repo
"""

import argparse
import os
import re
import sys

# ── Patterns ───────────────────────────────────────────────────────────────

# 40-char lowercase hex SHA — immutable.
SHA40_RE = re.compile(r'^[0-9a-f]{40}$')
# 7-39 char lowercase hex SHA — shortened commit, immutable in practice.
SHA_PARTIAL_RE = re.compile(r'^[0-9a-f]{7,39}$')

# Refs that are NOT version tags (HEAD, common branch names).
NON_TAG_REFS = frozenset({
    'HEAD', 'HEAD~1', 'HEAD^', 'HEAD~2', 'HEAD^^',
    'master', 'main', 'dev', 'develop', 'release',
    'stable', 'trunk', 'origin/HEAD', 'origin/main',
    'origin/master', 'origin/dev',
})

# Build files to scan, relative to repo root, in reporting order.
TARGET_FILES = [
    'Telegram/build/docker/centos_env/Dockerfile',
    'Telegram/build/prepare/prepare.py',
]

# Lines to look ahead for a pinning checkout/reset after a bare git clone.
PIN_WINDOW = 15

# Map file path → sort priority for deterministic output.
FILE_ORDER = {f: i for i, f in enumerate(TARGET_FILES)}


# ── Helpers ────────────────────────────────────────────────────────────────

def is_full_sha(ref):
    """True if ref is a 40-character lowercase hex SHA."""
    return bool(SHA40_RE.match(ref))


def is_partial_sha(ref):
    """True if ref is a 7-39 char lowercase hex SHA (shortened commit)."""
    return bool(SHA_PARTIAL_RE.match(ref))


def is_immutable_ref(ref):
    """True if ref is a full or partial commit SHA."""
    return is_full_sha(ref) or is_partial_sha(ref)


def is_non_tag_ref(ref):
    """True if ref is HEAD, a branch name, or similar (not a version tag)."""
    return ref in NON_TAG_REFS


def is_shell_variable(ref):
    """True if ref starts with $ (shell variable — cannot resolve statically)."""
    return ref.startswith('$')


def is_comment(line):
    """True if the line is a comment (# prefix after stripping whitespace)."""
    return line.lstrip().startswith('#')


def strip_git_c_prefix(line):
    """Normalize `git -C <dir> <cmd>` to `git <cmd>` for easier matching."""
    return re.sub(r'\bgit\s+-C\s+\S+\s+', 'git ', line, count=1)


def extract_b_tag(args):
    """Return the tag value after -b in a git clone argument string, or None."""
    m = re.search(r'(?:^|\s)-b\s+(\S+)', args)
    return m.group(1) if m else None


# ── Finding ────────────────────────────────────────────────────────────────

class Finding:
    """A single mutable git reference finding."""

    __slots__ = ('file', 'line', 'content', 'reason')

    def __init__(self, file, line, content, reason):
        self.file = file
        self.line = line
        self.content = content
        self.reason = reason

    def __lt__(self, other):
        """Sort by file (TARGET_FILES order) then line number."""
        return (
            FILE_ORDER.get(self.file, 999),
            self.line,
        ) < (
            FILE_ORDER.get(other.file, 999),
            other.line,
        )

    def format(self):
        """Return a human-readable, grep-friendly string."""
        return (
            f'[MUTABLE] {self.file}:{self.line}: {self.reason}\n'
            f'  | {self.content.strip()}'
        )


# ── Allowlist ──────────────────────────────────────────────────────────────

def load_allowlist(path):
    """Load allowlist entries from a file.

    Each non-comment line: ``relative_path:line_number``
    Returns a set of (relative_path, line_number) tuples.
    """
    entries = set()
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.rsplit(':', 1)
            if len(parts) == 2:
                try:
                    entries.add((parts[0], int(parts[1])))
                except ValueError:
                    pass  # skip malformed lines
    return entries


def is_allowlisted(allowlist, finding):
    """True if the finding matches an allowlist entry."""
    return (finding.file, finding.line) in allowlist


# ── Scanner ────────────────────────────────────────────────────────────────

def scan_file(filepath, repo_root, allowlist):
    """Scan a single file for mutable git references.

    Returns a list of Finding objects.
    """
    findings = []
    rel_path = os.path.relpath(filepath, repo_root).replace('\\', '/')

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Line number of a bare `git clone` (no -b) awaiting a pinning
    # checkout/reset-SHA.  None when no clone is pending.
    pending_clone = None

    for i, raw_line in enumerate(lines):
        line_no = i + 1
        line = raw_line.rstrip('\n')

        # ── Window expiry: flag unpinned clone after PIN_WINDOW lines ──
        if pending_clone is not None and (line_no - pending_clone) > PIN_WINDOW:
            content = lines[pending_clone - 1].rstrip('\n')
            finding = Finding(
                rel_path, pending_clone, content,
                f'git clone without explicit commit pinning '
                f'(no SHA checkout/reset within {PIN_WINDOW} lines)',
            )
            if not is_allowlisted(allowlist, finding):
                findings.append(finding)
            pending_clone = None

        # ── Skip comments ──
        if is_comment(line):
            continue

        normalized = strip_git_c_prefix(line)

        # ── git clone ──
        clone_match = re.search(r'\bgit\s+clone\b(.*)', normalized)
        if clone_match:
            # A new clone means the previous bare clone (if any) was never pinned.
            if pending_clone is not None:
                content = lines[pending_clone - 1].rstrip('\n')
                finding = Finding(
                    rel_path, pending_clone, content,
                    'git clone without explicit commit pinning '
                    '(no SHA checkout/reset before next clone)',
                )
                if not is_allowlisted(allowlist, finding):
                    findings.append(finding)
                pending_clone = None

            args = clone_match.group(1)
            b_tag = extract_b_tag(args)
            if b_tag is not None:
                # git clone -b <tag>
                if is_full_sha(b_tag):
                    pass  # immutable: clone -b <SHA>
                elif is_shell_variable(b_tag):
                    pass  # can't resolve statically — skip
                else:
                    finding = Finding(
                        rel_path, line_no, line,
                        f'git clone -b "{b_tag}" uses mutable tag '
                        f'(not a 40-hex SHA)',
                    )
                    if not is_allowlisted(allowlist, finding):
                        findings.append(finding)
                # clone has -b → no bare-clone pinning check needed
            else:
                # bare git clone (no -b) → needs subsequent checkout/reset SHA
                pending_clone = line_no
            continue

        # ── git checkout <ref> ──
        checkout_match = re.search(r'\bgit\s+checkout\s+(\S+)', normalized)
        if checkout_match:
            ref = checkout_match.group(1)
            if is_immutable_ref(ref):
                pending_clone = None  # SHA checkout pins a bare clone
            elif is_non_tag_ref(ref):
                pass  # HEAD or branch — not a mutable tag
            elif is_shell_variable(ref):
                pass  # can't resolve statically — skip
            else:
                finding = Finding(
                    rel_path, line_no, line,
                    f'git checkout "{ref}" uses mutable tag '
                    f'(not a SHA, not HEAD, not a branch)',
                )
                if not is_allowlisted(allowlist, finding):
                    findings.append(finding)
            continue

        # ── git fetch ... origin <ref> ──
        fetch_match = re.search(r'\bgit\s+fetch\b.*?\borigin\s+(\S+)', normalized)
        if fetch_match:
            ref = fetch_match.group(1)
            if is_full_sha(ref) or is_partial_sha(ref):
                pending_clone = None  # fetch by SHA pins a bare clone
            elif is_shell_variable(ref):
                pass  # can't resolve statically — skip
            else:
                finding = Finding(
                    rel_path, line_no, line,
                    f'git fetch origin "{ref}" uses mutable ref '
                    f'(not a SHA)',
                )
                if not is_allowlisted(allowlist, finding):
                    findings.append(finding)
            continue

        # ── git reset --hard <ref> ──
        reset_match = re.search(r'\bgit\s+reset\s+--hard\s+(\S+)', normalized)
        if reset_match:
            ref = reset_match.group(1)
            if ref == 'FETCH_HEAD' or is_immutable_ref(ref):
                pending_clone = None  # pins a bare clone
            continue

    # ── Handle pending clone at end of file ──
    if pending_clone is not None:
        content = lines[pending_clone - 1].rstrip('\n')
        finding = Finding(
            rel_path, pending_clone, content,
            'git clone without explicit commit pinning '
            '(no SHA checkout/reset before end of file)',
        )
        if not is_allowlisted(allowlist, finding):
            findings.append(finding)

    return findings


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Detect mutable git references in build scripts.',
    )
    parser.add_argument(
        '--allowlist', metavar='FILE', default=None,
        help='Path to an allowlist file (format: relative_path:line_number '
             'per line; # comments and blank lines are ignored).',
    )
    parser.add_argument(
        '--repo-root', metavar='DIR', default=None,
        help='Repository root directory (default: auto-detected from script '
             'location).',
    )
    args = parser.parse_args()

    # Determine repo root (script lives at <repo>/scripts/check_mutable_refs.py)
    if args.repo_root:
        repo_root = os.path.abspath(args.repo_root)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)

    # Load allowlist
    allowlist = load_allowlist(args.allowlist) if args.allowlist else set()

    # Scan all target files
    all_findings = []
    for rel_path in TARGET_FILES:
        filepath = os.path.join(repo_root, rel_path)
        if not os.path.isfile(filepath):
            print(f'[WARN] File not found: {rel_path}', file=sys.stderr)
            continue
        all_findings.extend(scan_file(filepath, repo_root, allowlist))

    # Sort for deterministic output
    all_findings.sort()

    # Report
    if all_findings:
        print(f'Found {len(all_findings)} mutable git reference(s):\n')
        for finding in all_findings:
            print(finding.format())
            print()
        print(f'Total: {len(all_findings)} mutable reference(s) detected.')
        print('Mutable tags and unpinned clones are a supply-chain risk.')
        print('Pin all dependencies to 40-hex commit SHAs.')
        sys.exit(1)
    else:
        print('No mutable git references found.')
        sys.exit(0)


if __name__ == '__main__':
    main()