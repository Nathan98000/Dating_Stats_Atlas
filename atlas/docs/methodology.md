# How the numbers are made

This page is written for visitors and kept in step with the counting
method itself — when the method changes, so does this page. The technical
record — decision documents, validation reports, and the precise
uncertainty figures — is in the project repository and available on
request.

## Where the data comes from

Every count on this site comes from the Census Bureau's American Community
Survey — the survey of about 3.5 million households a year that the
government uses to describe the whole country. We use the five years of
responses collected from 2020 through 2024, assigned to metro areas using
the Census Bureau's own geographic definitions. When we say "San
Francisco", we mean the whole metro area, not just the city limits.

Nobody is counted twice, nothing is scraped from dating apps, and no
number on this site comes from a model guessing — every figure is a count
of real survey responses, weighted the way the Census Bureau weights them.

## What we count

You describe who you're looking for — sex, ages, whether they've been
married before, education, income, race and ethnicity. We count how many
people matching that description live in each of 387 US cities. That
count is the **dating pool**.

**Dating pool balance** is a different, simpler number: all single men per
100 single women (or the mirror, if you're looking for women) in the ages
you picked. It deliberately ignores your other filters, so it means what
it sounds like — the shape of the whole singles scene at that age, which
doesn't change as you refine your search. In a same-sex search everyone is
on both sides of the comparison, so balance doesn't apply and the other
measures carry its weight.

**Race and ethnicity filters count who lives in a city and matches your
search — nothing more.** They say nothing about who dates or marries whom,
and this site makes no claim about that. Two groups are always included in
every count, whatever you tick: people of two or more races, and anyone
whose race isn't in the list. That's why a filtered pool can be a little
larger than the groups you ticked would suggest.

The rest of the score describes the place: typical rent and everyday
prices, places to go out and how walkable daily life is, nice days a year
and the student presence. Each stat's source is a named federal dataset —
Census, the Bureau of Economic Analysis, the EPA's walkability index, NOAA
climate normals, and federal education data. Crime is never part of any
score, in line with the FBI's own caution against using its data to rank
places.

## How the score works

You set what matters: the slider divides the people-side weight between
pool size and balance, and the three-step controls set how much cost,
going out, and weather count. Each city's stats are compared across the
cities that can answer your search, weighted the way you chose, and summed
to a score out of 100. "Not much" makes a thing count a little, not zero —
so nothing you deprioritise can silently vanish from the score. There are
no hidden weights: the controls on the home page are the whole model.

## When we leave a city out

Because the data is a survey, a very specific search can turn up only a
handful of matching responses in a smaller city. Below about a hundred
matching respondents, a count stops being dependable — so we leave that
city out of your results rather than show a number we can't stand behind,
and we say how many cities were left out and why. **Too few matches in the
survey is not the same as too few people in the country**: it usually
means the search is narrow, not that nobody fits.

We know how precise every count is — the survey publishes the machinery
for measuring it, and we validate ours against it on every build. We don't
print those precision figures on results pages; leaving out what's too
thin to trust, and saying so, is how this site expresses uncertainty. The
precise figures for any number on the site are available on request.

## What balance compares, exactly

Single (never-married, divorced or widowed) men aged X to Y, divided by
single women aged X to Y, where X to Y is the age range in your search —
counted across everyone in the metro area, before any education, income,
race or ethnicity filter. It is shown per 100, rounded to a whole number,
and it is only shown where both sides of the comparison have enough survey
sample to be dependable.

## Reproducibility

Every ranking this site has ever served can be reproduced exactly: the
build of the data and the version of the scoring model are pinned inside
every result the server produces, and changes to either are versioned and
tested against pinned expectations. The full decision history — including
what changed between model versions and why — is in the project's decision
records.
