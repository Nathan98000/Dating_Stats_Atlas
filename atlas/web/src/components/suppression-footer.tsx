import Link from "next/link";
import type { Meta, RankResponse } from "@/lib/types";
import { fmtInt, REASON_ORDER } from "@/lib/format";

/** The permanent footer under every list (§5.3, gate 3): the excluded
 * metros as counts with reasons and a link to the policy — never silently
 * absent. shown_unranked is a permanently empty array since ADR 0002 and
 * renders ONLY if it is somehow non-empty; a "0 metros shown but not
 * ranked" line never renders. */
export function SuppressionFooter({
  response,
  meta,
}: {
  response: RankResponse;
  meta: Meta;
}) {
  const { counts } = response;
  const policy = meta.policy_strings;
  const reasons = Object.entries(counts.suppressed_by_reason).sort(
    (a, b) => REASON_ORDER.indexOf(a[0]) - REASON_ORDER.indexOf(b[0]),
  );
  return (
    <aside
      aria-label="Metros not ranked for this query"
      className="mt-6 border-t border-rule pt-4 text-sm text-ink-2"
      data-testid="suppression-footer"
    >
      {response.shown_unranked.length > 0 && (
        <p>
          <strong className="num">{fmtInt(response.shown_unranked.length)}</strong>{" "}
          metros are shown with their margins but not ranked.
        </p>
      )}
      {counts.suppressed > 0 ? (
        <div>
          <p>
            <strong className="num text-ink">{fmtInt(counts.suppressed)}</strong> of{" "}
            <span className="num">{fmtInt(counts.universe)}</span> metros are
            suppressed for this query rather than guessed:
          </p>
          <ul className="mt-1 flex flex-col gap-0.5">
            {reasons.map(([reason, n]) => (
              <li key={reason}>
                <span className="num text-ink">{fmtInt(n)}</span> —{" "}
                {policy[reason] ?? reason}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>
          Every metro in the ranked set has enough sample for this query —
          nothing is suppressed.
        </p>
      )}
      <p className="mt-2">
        <Link
          href="/methodology#suppression"
          className="text-accent underline underline-offset-2"
        >
          How suppression is decided
        </Link>
        <span className="text-ink-3"> · </span>
        <Link
          href="/methodology#margins"
          className="text-accent underline underline-offset-2"
        >
          What the margins mean
        </Link>
      </p>
    </aside>
  );
}
