import type { BalanceBlock, Meta } from "@/lib/types";
import { balancePosition, fill } from "@/lib/results";
import { InfoTip } from "./info-tip";

/** Dating pool balance as one track (Phase 5; replaces the v3 tally bars
 * everywhere): a 120x8px --data-neutral track spanning 40 to 160 per 100,
 * clamped, a 2px tick at 100 (even), and a dot at the served per_100 —
 * more of the sought sex to the right. Beneath it the served words ("More
 * women" · "Even" · "More men"), then the API's own display string, then
 * the short caption with the full balance_caption behind an info tip.
 * Never a number the API didn't send: the dot's place is presentation
 * scaling of per_100, and a row without a figure shows the API's note. */
export function BalanceTrack({
  balance,
  meta,
  id,
  caption = true,
}: {
  balance: BalanceBlock;
  meta: Meta;
  id: string;
  caption?: boolean;
}) {
  const s = meta.policy_strings;
  if (!balance.available || balance.per_100 == null) {
    return (
      <p className="text-body-sm text-ink-3" data-testid="balance-tally">
        {balance.note}
      </p>
    );
  }
  const x = balancePosition(balance.per_100) * 100;
  return (
    <div className="flex flex-col gap-2" data-testid="balance-tally">
      <div aria-hidden="true" className="w-full max-w-[176px]">
        <div className="relative mx-auto my-1 h-2 w-full max-w-[120px] rounded-full bg-data-neutral" data-testid="balance-track">
          <span className="absolute -top-[5px] left-1/2 h-[18px] w-0.5 -translate-x-1/2 bg-ink-3" />
          <span
            className="absolute -top-1 h-4 w-4 -translate-x-1/2 rounded-full border-[3px] border-surface bg-ink shadow-[0_0_0_1px_var(--ink)]"
            style={{ left: `${x}%` }}
            data-testid="balance-dot"
          />
        </div>
        <div className="mt-1.5 flex flex-wrap justify-between gap-x-1.5 text-overline font-normal tracking-normal text-ink-3">
          <span>{fill(s.balance_more, { word: balance.seeker_word ?? "" })}</span>
          <span>{s.balance_even}</span>
          <span>{fill(s.balance_more, { word: balance.sought_word ?? "" })}</span>
        </div>
      </div>
      <p className="text-body-sm font-semibold">
        <span className="sr-only">{meta.features.pool_balance.display_name}: </span>
        {balance.display}
      </p>
      {caption && (
        <p className="flex items-start gap-1 text-caption text-ink-3">
          <span>{s.balance_short_caption}</span>
          <InfoTip id={`${id}-bal-info`} label={s.balance_label}>
            {s.balance_caption}
          </InfoTip>
        </p>
      )}
    </div>
  );
}
