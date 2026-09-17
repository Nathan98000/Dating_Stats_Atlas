# How the numbers are made

**In a minute:** every count on this site comes from the Census Bureau's
American Community Survey — five years of it, 2020 through 2024. You
describe who you're looking for; we count how many such people live in
each of 387 US metro areas, add a few facts about each place from named
federal datasets, and weight it all the way you choose. Nothing is
scraped from dating apps, nothing is guessed by a model, and when the
survey is too thin to answer a search in some city, we leave that city
out and say so instead of publishing a shaky number.

This page is kept in step with the counting method itself — when the
method changes, so does this page. The technical record — decision
documents, validation reports, and precise uncertainty figures — is in
the project repository and available on request.

## Where does the data come from?

- **People counts** — the American Community Survey, about 3.5 million
  households a year, 2020–2024 combined, weighted the way the Census
  Bureau weighs them. Metro areas follow the government's own
  definitions: "San Francisco" means the whole metro area, not the city
  limits.
- **Place stats** — each from one named federal source, updated when
  that source publishes:

| Stat | Source |
| --- | --- |
| Rent | Census Bureau (American Community Survey) |
| Everyday prices | Bureau of Economic Analysis price levels |
| Places to go out | Census Bureau business data |
| Getting around on foot | EPA's national walkability index |
| Nice days a year | NOAA daily weather-station records, 1991–2020 |
| Students | Federal education data (IPEDS) |
| Reported crime | FBI Crime Data Explorer — shown, never scored |

## What does a "match" count?

Everyone in a metro area who fits your whole search — sex, age range,
never married or previously married, and any education, income, race or
ethnicity filters you set. That count is the **dating pool**, and it is
the biggest part of the score.

## What does balance compare?

**Dating pool balance** is a simpler number: all single men per 100
single women (or the mirror, if you're looking for women) in the age
range you picked — never-married, divorced or widowed people, counted
across the whole metro, **before any education, income, race or ethnicity
filter**. It deliberately ignores your other filters so it means what it
sounds like: the shape of the whole singles scene at that age, which
doesn't move as you refine your search. It's shown per 100, rounded to a
whole number, and only where both sides of the comparison have enough
survey sample to be dependable.

In a same-sex search everyone is on both sides of the comparison, so
balance doesn't apply and the other measures carry its weight.

## What do the race and ethnicity boxes do?

They select **who is counted as living in a city and matching your
search — nothing more**. They say nothing about who dates or marries
whom, and this site makes no claim about that.

**Two groups are always included in every count, whatever you tick:
people of two or more races, and anyone whose race isn't in the list.**
That's a deliberate rule — those two groups fit any selection — and it's
why a filtered pool can be a little larger than the boxes you ticked
would suggest. Unticking every box means the same as ticking all six:
no filter at all.

## How does the score work?

You set what matters. The slider divides the people-side weight between
pool size and balance; four controls — cost of living, social life,
student life, weather — set how much each place stat counts. "Not much"
makes a thing count a little, not zero, so nothing you deprioritise can
silently vanish. Each city's stats are compared across the cities that
can answer your search, weighted your way, and summed to a score out
of 100. There are no hidden weights: the controls on the home page are
the whole model.

## Why do some searches leave cities out?

Because the data is a survey. A very specific search can turn up only a
handful of matching responses in a smaller city, and below about a
hundred matching respondents a count stops being dependable — so we
leave that city out of your results and say how many were left out.
**Too few matches in the survey is not the same as too few people in the
country**: it usually means the search is narrow, not that nobody fits.

## Why aren't margins of error printed on every number?

We measure how precise every count is — the survey publishes the
machinery, and we validate ours against it on every build. But a page of
plus-or-minus figures helps almost nobody. Instead, precision is
expressed by **leaving out** what's too thin to trust, and saying so.
The precise figures behind any number on the site are available on
request.

## Why is crime shown but never ranked?

Police agencies report to the FBI voluntarily, and different shares of
each city's agencies report in any year — so two cities' crime figures
aren't comparable, and the FBI itself cautions against ranking places by
them. City pages show reported crime with the share of the metro's
population its figures actually cover; crime is never part of any score;
and there is deliberately no "cities by crime" list.
[More about the crime figures.](/about-crime-data)

## Every city by one measure

Preference-free lists of every ranked city, straight from the build:

- [Cities by rent](/stats/median_gross_rent)
- [Cities by everyday prices](/stats/everyday_prices)
- [Cities by places to go out](/stats/venues_per_100k)
- [Cities by getting around on foot](/stats/resident_walkability_index)
- [Cities by nice days a year](/stats/pleasant_days)
- [Cities by students](/stats/students_per_1k_adults)
- [Cities by population](/stats/who_lives_here)

## Can a result be reproduced later?

Yes — exactly. The build of the data and the version of the scoring
model are pinned inside every result the server produces, and changes to
either are versioned and tested against pinned expectations. The full
decision history — what changed between model versions and why — is in
the project's decision records.
