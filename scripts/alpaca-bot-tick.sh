#!/usr/bin/env bash
set -euo pipefail

# Persistent state and logs (mount /data in Coolify)
STATE_DIR="/data/alpaca-bot"
LOG_DIR="/var/log/alpaca-bot"
STATE_JSON="${STATE_DIR}/state.json"
PLAN_MD="${STATE_DIR}/plan.md"
ACTIONS_NDJSON="${LOG_DIR}/actions.ndjson"

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

if [ ! -f "${STATE_JSON}" ]; then
  cat > "${STATE_JSON}" <<'JSON'
{
  "last_tick_iso": null,
  "positions_note": "Set by bot every run. Human can add notes.",
  "plan": "Initial plan: maintain risk limits, avoid overtrading, review P/L and buying power.",
  "actions_history": []
}
JSON
fi

if [ ! -f "${PLAN_MD}" ]; then
  cat > "${PLAN_MD}" <<'MD'
Trading Bot Plan
- Objective: Preserve capital, seek asymmetric entries, limit exposure
- Cadence: Evaluate every 15 minutes; only place orders during open market
- Rules:
  - Maintain single-source-of-truth state.json, append action logs as NDJSON
  - Always re-derive current positions before acting
  - Propose actions only with explicit rationale and risk note
MD
fi

LASH_CMD="${LASH_CMD:-lash}"

TS="$(date -Iseconds)"
TMP_OUT="$(mktemp)"
TMP_PROMPT="$(mktemp)"

cat > "${TMP_PROMPT}" <<'PROMPT'
You are a cautious Alpaca trading operator using the MCP server.
- Read and summarize current positions, P/L, and buying power.
- Update plan.md if your plan changes; keep it short and concrete.
- Emit a machine-readable JSON block with keys: decisions[], notes, updatedPlan?, risk.
- Decisions must be no-ops unless conviction is high AND market is open.
- If market is closed, only log observations and plan adjustments.

Return ONLY one fenced JSON block with this structure:
{
  "decisions": [
    {"action": "none" | "buy" | "sell" | "close", "symbol": "TICKER", "qty": number, "type": "market|limit", "limitPrice": number|null, "why": "short reason"}
  ],
  "notes": "brief status",
  "updatedPlan": "optional short plan delta or null",
  "risk": "key risk to watch"
}
PROMPT

CONTEXT="$(jq -c '.' "${STATE_JSON}")"

{
  echo "SYSTEM:"
  cat "${PLAN_MD}"
  echo
  echo "CONTEXT_JSON:"
  echo "${CONTEXT}"
  echo
  echo "PROMPT:"
  cat "${TMP_PROMPT}"
} | ${LASH_CMD} > "${TMP_OUT}"

JSON_BLOCK="$(awk '/^\s*```/{f^=1;next} f' "${TMP_OUT}" | tr -d '\r' || true)"
if [ -z "${JSON_BLOCK}" ]; then
  JSON_BLOCK="$(cat "${TMP_OUT}")"
fi

if ! echo "${JSON_BLOCK}" | jq -e . >/dev/null 2>&1; then
  JSON_BLOCK="$(jq -n --arg ts "${TS}" --arg raw "$(tr -d '\000' < "${TMP_OUT}" | head -c 5000)" \
    '{decisions:[], notes:"Non-JSON output captured", updatedPlan:null, risk:"n/a", raw: $raw}')"
fi

jq -c --arg ts "${TS}" '. | .ts=$ts' <<< "${JSON_BLOCK}" >> "${ACTIONS_NDJSON}"

UPDATED_PLAN="$(jq -r '.updatedPlan // empty' <<< "${JSON_BLOCK}" || true)"
if [ -n "${UPDATED_PLAN}" ]; then
  {
    echo "Last updated: ${TS}"
    echo
    echo "${UPDATED_PLAN}"
  } > "${PLAN_MD}"
fi

jq -n \
  --arg ts "${TS}" \
  --slurpfile prev "${STATE_JSON}" \
  --slurpfile lastAct <(tail -n 1 "${ACTIONS_NDJSON}" 2>/dev/null || echo '{}') \
  '
  {
    last_tick_iso: $ts,
    plan: ($prev[0].plan // "see plan.md"),
    actions_history: (($prev[0].actions_history // []) + [$lastAct[0]] ) | (.[-50:] // .),
    positions_note: ($prev[0].positions_note // "")
  }
  ' > "${STATE_JSON}.new"

mv "${STATE_JSON}.new" "${STATE_JSON}"

rm -f "${TMP_OUT}" "${TMP_PROMPT}"
echo "[${TS}] tick complete"


