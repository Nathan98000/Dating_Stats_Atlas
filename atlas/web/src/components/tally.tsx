import type { BalanceBlock } from "@/lib/types";
import { FemaleMark, MaleMark } from "./chrome";

/** Dating pool balance as two tally rows (the v3 boards): one 7×16px bar
 * per 10, a partial bar for the remainder, ♂/♀ marks, captioned in the
 * API's words. The seeker row is always ten bars (the "per 100"
 * baseline). Never renders a number the API didn't send. */
export function BalanceTally({
  balance,
  compact = false,
}: {
  balance: BalanceBlock;
  compact?: boolean;
}) {
  if (!balance.available) {
    return (
      <p className={`text-ink-3 ${compact ? "text-[12.5px]" : "text-sm"}`}>
        {balance.note}
      </p>
    );
  }
  const per100 = balance.per_100!;
  const soughtMale = balance.sought_word === "men";
  const seekerMale = balance.seeker_word === "men";
  return (
    <div className="flex flex-col gap-1.5">
      <span className="sr-only">
        Dating pool balance: {balance.display}.
      </span>
      <div aria-hidden="true" className="flex flex-col gap-1.5">
        <TallyRow
          count={per100 / 10}
          color={soughtMale ? "var(--male)" : "var(--female)"}
          mark={soughtMale ? <MaleMark /> : <FemaleMark />}
        />
        <TallyRow
          count={10}
          color={seekerMale ? "var(--male)" : "var(--female)"}
          mark={seekerMale ? <MaleMark /> : <FemaleMark />}
        />
      </div>
      <span aria-hidden="true" className={`text-ink-3 ${compact ? "text-[12.5px]" : "text-[13px]"}`}>
        {balance.display}
      </span>
    </div>
  );
}

function TallyRow({
  count,
  color,
  mark,
}: {
  count: number;
  color: string;
  mark: React.ReactNode;
}) {
  const full = Math.floor(count);
  const frac = count - full;
  return (
    <div className="flex items-center gap-[9px]">
      {mark}
      <div className="flex gap-[3px]">
        {Array.from({ length: full }).map((_, i) => (
          <span
            key={i}
            className="h-4 w-[7px] rounded-[2px]"
            style={{ background: color }}
          />
        ))}
        {frac > 0.05 && (
          <span
            className="h-4 rounded-[2px]"
            style={{ background: color, width: `${Math.max(2, Math.round(frac * 7))}px` }}
          />
        )}
      </div>
    </div>
  );
}
