import type { BalanceBlock, Meta } from "@/lib/types";
import { balanceDots } from "@/lib/results";
import { InfoTip } from "./info-tip";

/** Dating pool balance as people (Nathan, 2026-10-10: the track replaced
 * everywhere it showed — the row and card detail, the city page, Compare):
 * the API's own sentence ("118 men per 100 women"), then one dot for every
 * ten singles. The other sex's row is the hundred, ten dots; the sought
 * sex's row is the served per_100 in tens, its last dot filled to the
 * fraction, so "118" reads as eleven dots and most of a twelfth. A
 * hairline in its own gutter after the tenth dot marks even. The dots are
 * presentation scaling of the served per_100 (40 to 160, clamped, an end
 * mark past 160), never a new number; neutral colours, since balance is
 * shown and never scored. Where the figure has under 230px (a phone's
 * Compare column), each row's word sits above its dots. A row without a
 * figure shows the API's note. The caption's box reads balance_caption on
 * every search (its same-sex form was deleted on 2026-10-10, Nathan). */
export function BalanceDots({
  balance,
  meta,
  id,
  caption = true,
  tile = false,
}: {
  balance: BalanceBlock;
  meta: Meta;
  id: string;
  caption?: boolean;
  /** the row and card detail: the section's information box carries the
   * caption */
  tile?: boolean;
}) {
  const s = meta.policy_strings;
  if (!balance.available || balance.per_100 == null) {
    return (
      <p className="text-body-sm text-ink-3" data-testid="balance-tally">
        {balance.note}
      </p>
    );
  }
  const sought = balanceDots(balance.per_100);
  return (
    <div className="flex w-full flex-col gap-2.5" data-testid="balance-tally">
      <p className={tile ? "text-body font-semibold" : "text-body-sm font-semibold"}>
        <span className="sr-only">{meta.features.pool_balance.display_name}: </span>
        {balance.display}
      </p>
      <div aria-hidden="true" className="@container w-full max-w-[256px]" data-testid="balance-dots">
        <div className="flex flex-col gap-[5px] text-caption @max-[229px]:gap-1.5">
          <Row word={balance.seeker_word} wordClass="text-ink-3">
            <Dots full={10} part={0} className="text-data-neutral" row="seeker" />
          </Row>
          <Row word={balance.sought_word} wordClass="font-medium text-ink-2">
            <Dots full={sought.full} part={sought.part} className="text-ink" row="sought" more={sought.beyond} />
          </Row>
          <Row word="">
            <span className={TRACKS}>
              <span className="col-start-11 justify-self-center whitespace-nowrap text-overline font-normal leading-none tracking-normal text-ink-3">
                {s.balance_even}
              </span>
            </span>
          </Row>
        </div>
      </div>
      {caption && !tile && (
        <p className="flex items-start gap-1 text-caption text-ink-3">
          <span>{s.balance_short_caption}</span>
          <InfoTip id={`${id}-bal-info`} label={s.balance_info_label}>
            {s.balance_caption}
          </InfoTip>
        </p>
      )}
    </div>
  );
}

/** ten dot tracks, the even gutter, six more */
const TRACKS = "grid grid-cols-[repeat(10,minmax(0,1fr))_7px_repeat(6,minmax(0,1fr))] items-center " +
  "gap-x-[3px] @max-[229px]:gap-x-[2px]";

/** a row's word beside its dots, or above them where the figure is narrow */
function Row({ word, wordClass = "", children }: {
  word: string | undefined; wordClass?: string; children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[3.4em_minmax(0,1fr)] items-center gap-x-2 @max-[229px]:grid-cols-1 @max-[229px]:gap-y-0.5">
      <span className={`leading-none ${wordClass} ${word ? "" : "@max-[229px]:hidden"}`}>{word}</span>
      {children}
    </div>
  );
}

/** `full` whole dots, then one filled to `part` (0-1) when there is a
 * remainder, an end mark past the row (`more`), and the row's stretch of
 * the even line in the gutter; the two rows' stretches meet across the gap */
function Dots({ full, part, className, row, more = false }: {
  full: number; part: number; className: string; row: string; more?: boolean;
}) {
  const col = (i: number) => ({ gridColumn: i < 10 ? i + 1 : i + 2 });
  return (
    <span className={`relative ${TRACKS} ${className}`} data-row={row} data-full={full}
      data-part={part > 0 ? part.toFixed(1) : undefined}>
      {Array.from({ length: full }, (_, i) => (
        <span key={i} className="aspect-square rounded-full bg-current" style={col(i)} />
      ))}
      {part > 0 && (
        <span className="relative aspect-square overflow-hidden rounded-full bg-current/20" style={col(full)}>
          <span className="absolute inset-y-0 left-0 bg-current" style={{ width: `${part * 100}%` }} />
        </span>
      )}
      <span className="col-start-11 row-start-1 -my-[3px] w-px justify-self-center self-stretch bg-line-strong" />
      {more && (
        <span className="absolute -right-3 top-1/2 -translate-y-1/2 text-overline leading-none text-ink-3">+</span>
      )}
    </span>
  );
}
