# Data dictionary

Canonical keys: dataset + indicator + geography + period + unit + frequency. Value is finite numeric; period is ISO date; provenance URL is required HTTPS. Units are never merged silently.

KP census: population, male/female/transgender counts (persons); population density (persons/km²); urban share (%); household size (persons/household); published annual population growth (%). 2017 population uses source comparison column. Geography is the district label, title-normalized. Province totals and rural/urban/tehsil subrows are excluded. Boundary changes can invalidate simple historical comparisons.

Price dataset: cpi_national, cpi_urban, cpi_rural, wpi; unit index_2015_16_100; monthly. Urban/rural describe national population strata, not district geography. Annual summary row and old-base indices are excluded. The PDF's separate YoY table is not mixed with index levels.
