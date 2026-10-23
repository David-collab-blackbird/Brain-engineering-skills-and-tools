#!/bin/bash
# Run `claude` inside an isolated sandbox for one E15 arm run.
#
# usage: sandbox_claude.sh RUNDIR -- <claude args...>
#   RUNDIR/work  = the repository the builder works in (cwd)
#   RUNDIR/home  = HOME for this run (sessions, transcripts, settings)
#
# Isolation (why: hidden tests, the reference solution, other runs and this
# engineer session must be unreachable from the builder):
#   * private mount + PID namespaces; tmpfs over /home/claude, /root and /tmp;
#     only RUNDIR and the CLI's auth directory are bound back in;
#   * all Linux capabilities dropped (root without CAP_SYS_ADMIN cannot unmount
#     the tmpfs; without CAP_DAC_OVERRIDE/CAP_FOWNER it cannot write files owned
#     by another user, which is how read-only acceptance tests are enforced);
#   * a clean environment (env -i) with only proxy/CA variables, the shared
#     venv on PATH, telemetry opt-outs and per-arm extras from E15_EXTRA_ENV.
set -euo pipefail
RUNDIR=$(readlink -f "$1"); shift
[ "$1" = "--" ] && shift
HOLD=/run/e15hold.$$
EXTRA_ENV=${E15_EXTRA_ENV:-}
exec unshare --mount --pid --fork --mount-proc --propagation private bash -c '
set -euo pipefail
RUNDIR="$1"; HOLD="$2"; EXTRA_ENV="$3"; shift 3
mkdir -p "$HOLD"; mount -t tmpfs tmpfs "$HOLD"
mkdir -p "$HOLD/run" "$HOLD/auth"
mount --bind "$RUNDIR" "$HOLD/run"
mount --bind /home/claude/.claude/remote "$HOLD/auth"
mount -t tmpfs tmpfs /home/claude
mkdir -p "$RUNDIR" /home/claude/.claude/remote
mount --bind "$HOLD/run" "$RUNDIR"
mount --bind "$HOLD/auth" /home/claude/.claude/remote
mount -t tmpfs tmpfs /root
mount -t tmpfs tmpfs /tmp
umount -l "$HOLD" 2>/dev/null || true
cd "$RUNDIR/work"
exec setpriv --inh-caps=-all --ambient-caps=-all --bounding-set=-all -- \
  env -i HOME="$RUNDIR/home" USER=root LOGNAME=root SHELL=/bin/bash TERM=dumb LANG=C.UTF-8 \
    PATH=/opt/e15/venv/bin:/opt/node22/bin:/usr/local/bin:/usr/bin:/bin \
    HTTPS_PROXY="$HTTPS_PROXY" https_proxy="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY" \
    SSL_CERT_FILE=/opt/e15/ca-bundle.crt NODE_EXTRA_CA_CERTS=/opt/e15/ca-bundle.crt \
    REQUESTS_CA_BUNDLE=/opt/e15/ca-bundle.crt \
    IS_SANDBOX=1 DISABLE_AUTOUPDATER=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    SUPERPOWERS_DISABLE_TELEMETRY=1 PYTHONDONTWRITEBYTECODE=1 CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 \
    $EXTRA_ENV \
    claude "$@" < /dev/null
' bash "$RUNDIR" "$HOLD" "$EXTRA_ENV" "$@"
