#!/usr/bin/env bash
# merge-surface-sweep.sh — fail when the ADDED lines of a merge surface carry a secret-SHAPED value.
#
# Classes (shape only; this file carries no literal secret, slug or identifier):
#   hex32       32-hex run          (capability slugs, account ids, md5-shaped ids)
#   base32-25   base32 run of 25 OR MORE (a8t capability slugs; requires at least one digit)
#   digits12    12-digit run        (cloud account-id form; the noisiest class — compact timestamps also hit)
#   basic-auth  Authorization Basic <base64>
#   glc-token   glc_<token>
#   aws-key-id  AKIA/ASIA/AROA/AIDA + 16
#   email       real-looking e-mail, excluding decorator forms (no local part), example.*/localhost, and any domain
#               listed in SWEEP_ALLOW_EMAIL_DOMAINS (comma-separated; the operator's own contact domains)
#
# Modes:
#   --range <base>...<head>   sweep the ADDED lines of `git diff` over that range (three-dot: merge-base)
#   --lines <file>            sweep raw lines from a file (file:line reported as <file>:<n>)
#   --self-test               positive control (fixture built at runtime MUST fail) + negative control (clean MUST pass)
#
# Output: one "class<TAB>file:line" per hit and a per-class summary. The matched TEXT is NEVER printed:
# this repository is public and so are its Actions logs.
# Exit: 0 = clean, 1 = hits found, 2 = usage/engine error.
set -euo pipefail

SKIP_PATHS='^(uv\.lock|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|\.github/scripts/merge-surface-sweep\.sh)$'
export SKIP_PATHS

# stdin: "file<TAB>line<TAB>text" ; stdout: "class<TAB>file:line"
classify() {
  perl -ne '
    BEGIN { our %ALLOW = map { lc($_) => 1 } grep { length } split(/\s*,\s*/, $ENV{SWEEP_ALLOW_EMAIL_DOMAINS} // ""); }
    sub allowed_domain { my $d = lc(shift); return 1 if $ALLOW{$d}; for my $a (keys %ALLOW) { return 1 if $d =~ /(?:^|\.)\Q$a\E$/ } 0 }
    chomp;
    my ($f, $n, $t) = split(/\t/, $_, 3);
    $t = "" unless defined $t;
    next if $f =~ /$ENV{SKIP_PATHS}/;
    my @hits;
    push @hits, "hex32"      if $t =~ /(?<![0-9A-Fa-f])[0-9a-f]{32}(?![0-9A-Fa-f])/;
    push @hits, "base32-25"  if $t =~ /(?<![a-z2-7])(?=[a-z2-7]{25,}(?![a-z2-7]))(?=[a-z]*[2-7])[a-z2-7]{25,}/;
    push @hits, "digits12"   if $t =~ /(?<![0-9])[0-9]{12}(?![0-9])/;
    push @hits, "basic-auth" if $t =~ /Authorization[[:space:]]*[:=][[:space:]]*["'"'"']?Basic[[:space:]]+[A-Za-z0-9+\/=]{16,}/i;
    push @hits, "glc-token"  if $t =~ /glc_[A-Za-z0-9+\/=_-]{20,}/;
    push @hits, "aws-key-id" if $t =~ /(?<![A-Z0-9])(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}(?![A-Z0-9])/;
    push @hits, "email"      if $t =~ /(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![A-Za-z0-9])/
                              && $t !~ /@(?:example\.(?:com|org|net)|localhost)(?![A-Za-z0-9])/i
                              && !allowed_domain($1);
    print "$_\t$f:$n\n" for @hits;
  '
}

# $1 = git range ; stdout: "file<TAB>line<TAB>text" for every ADDED line
added_lines() {
  git diff --unified=0 --no-color --no-ext-diff "$1" -- . | perl -ne '
    if (/^\+\+\+ (?:b\/)?(.*)$/)                          { $f = $1; next }
    if (/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/)          { $n = $1; next }
    if (/^\+(.*)$/ && defined $f)                         { print "$f\t$n\t$1\n"; $n++; next }
  '
}

report() {  # stdin: "class<TAB>file:line" ; prints hits + summary; returns 1 if any
  local hits; hits=$(cat)
  if [ -z "$hits" ]; then echo "merge-surface sweep: CLEAN (0 hits)"; return 0; fi
  echo "merge-surface sweep: HITS (text withheld)"
  printf '%s\n' "$hits" | sort | uniq
  echo "--- per class ---"
  printf '%s\n' "$hits" | cut -f1 | sort | uniq -c | sed 's/^ *//'
  return 1
}

self_test() {
  local r32 b25 d12 b64 g24 a16
  r32=$(printf 'a%.0s' $(seq 32)); b25="$(printf 'b%.0s' $(seq 24))3"; d12=$(printf '1%.0s' $(seq 12))
  b64=$(printf 'QUJD%.0s' $(seq 5)); g24=$(printf 'x%.0s' $(seq 24)); a16=$(printf 'A%.0s' $(seq 16))
  local pos neg
  pos=$(printf 'fixture\t1\tid=%s\nfixture\t2\tslug=%s\nfixture\t3\taccount=%s\nfixture\t4\tAuthorization: Basic %s\nfixture\t5\ttoken=glc_%s\nfixture\t6\tkey=AKIA%s\nfixture\t7\tcontact=person@corp.invalid\nfixture\t8\tslug26=%s7\n' \
        "$r32" "$b25" "$d12" "$b64" "$g24" "$a16" "$b25")
  neg=$(printf 'clean\t1\tdef route(): pass\nclean\t2\t@pytest.fixture\nclean\t3\t@router.get("/x")\nclean\t4\tsha256: %s%s\nclean\t5\t20260906T180854Z\nclean\t6\tuser@example.com\nclean\t7\tabcdefghijklmnopqrstuvwxy\n' "$r32" "$r32")
  local pn nn
  pn=$(printf '%s\n' "$pos" | classify | wc -l | tr -d ' ')
  nn=$(printf '%s\n' "$neg" | classify | wc -l | tr -d ' ')
  echo "self-test: positive control hits=$pn (expected 8) ; negative control hits=$nn (expected 0)"
  if [ "$pn" -ne 8 ]; then echo "self-test FAIL: positive control did not fail as required"; return 2; fi
  if [ "$nn" -ne 0 ]; then echo "self-test FAIL: negative control produced hits"; return 2; fi
  echo "self-test PASS: the engine can fail, and does not fail on clean input"
}

case "${1:-}" in
  --self-test) self_test ;;
  --range)     [ -n "${2:-}" ] || { echo "usage: --range <base>...<head>" >&2; exit 2; }
               added_lines "$2" | classify | report ;;
  --lines)     [ -f "${2:-}" ] || { echo "usage: --lines <file>" >&2; exit 2; }
               awk -v f="$2" '{ printf "%s\t%d\t%s\n", f, NR, $0 }' "$2" | classify | report ;;
  *)           echo "usage: $0 --self-test | --range <base>...<head> | --lines <file>" >&2; exit 2 ;;
esac
