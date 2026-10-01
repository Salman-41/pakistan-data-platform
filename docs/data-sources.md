# Verified source inventory

Research date: 2026-10-01. This inventory distinguishes a verified published link, a successful byte download, and a validated observation count. None implies the others. Public accessibility is not an open-data licence. Source files are excluded from the software licence and Git history; redistribution needs dataset-specific review.

## Decision

Start with PBS Census 2023 Excel tables and PBS historical price-index publications. These provide genuine geographic detail and a continuous monthly forecasting series. Use official crop and labour publications next. Keep SBP, trade dashboards and NEPRA adapters configurable and fail visibly when access is unavailable. Do not invent an API or copy national indicators into districts. The first demonstrable warehouse is a modest authentic corpus; a million-observation claim is not yet supported by acquisition evidence.

## Source matrix

| Organization / dataset | Verified source | Format / automation | Geographic and temporal coverage | Observed status and rights |
|---|---|---|---|---|
| PBS Census 2023 | https://www.pbs.gov.pk/census/ and https://www.pbs.gov.pk/result-excel/ | Published Excel and PDF links. Parse workbooks with explicit table-specific headers rather than scrape the landing page. | National, province, district and some lower-level rows; census year 2023, Table 1 includes prior-census comparison/growth. | 304 unique .xlsx links observed in landing-page HTML; two KP workbooks successfully downloaded. PBS footer says all rights reserved; no blanket permissive licence verified. |
| PBS historical CPI/WPI | https://www.pbs.gov.pk/price-statistics/ | Historical PDF, linked Excel item-price sheets and published monthly reports. PDF extraction must validate year/month rows and base year. | National and urban/rural domains. Historical index PDF has monthly entries July 2017–June 2026 plus a fiscal-year aggregate that must not be converted into a month. | Published PDF text verified. Preserve index levels separately from published YoY rates. |
| PBS SPI | Same price-statistics landing page | Weekly report/annexure links; landing table populated dynamically. Direct official PDF/Excel attachments preferred. | Weekly; basket/item/city granularity depends on attachment. | Listing verified, complete archive count not measured. Market-collection counts on methodology page are not released observation counts. |
| PBS agriculture | https://www.pbs.gov.pk/web/?page_id=10374 | Historical district PDF plus linked statistical tables. Download specific publication; page contains unrelated template examples. | District/province, crop, fiscal year; historical publication 1981-82–2008-09. | 214-page historical PDF downloaded (2,216,995 bytes). Observation rows not yet parsed or counted. Official crop estimates can be provisional or survey/opinion based, not individual farm records. |
| PBS labour | https://www.pbs.gov.pk/labour-force-statistics/ | PDF statistical tables and annual reports; explicit table IDs. | 2024-25 and older rounds. Province, sex, age, rural/urban supported by selected tables. | Table 15 published PDF verified, five pages. Do not treat survey sample count as downloadable row count or assume every table estimates districts. |
| PBS PSLM | https://www.pbs.gov.pk/pslm-3/ | Published reports/coding-scheme/microdata section. Dataset-specific conditions and survey weights require review before microdata ingestion. | District survey rounds 2004-05 through 2019-20 shown; 2026 fieldwork described as in progress. | Landing page verified. Completed downloads/row counts not claimed. |
| PBS national accounts | https://www.pbs.gov.pk/national-accounts-2/ and https://na.data.gov.pk/ | Published statistical tables; dashboard is HTML/JavaScript, no documented public API verified. | GDP and sectors, national/fiscal-year and quarterly tables where published. | Pages verified. Website display is not a guaranteed machine-readable endpoint. |
| SBP EasyData | https://easydata.sbp.org.pk/ | Public portal/export intended, but no supported API contract verified in this environment. Manual official export import is a reproducible alternative. | Depends on series/frequency. | HTTP 403 in both web retrieval and direct urllib attempt. No rows acquired. Do not circumvent denial or assert millions ingested. |
| SBP economic data | https://www.sbp.org.pk/economic-data and https://www.sbp.org.pk/ecodata/index2.asp | Official HTML/download tables expected; direct URL needs source-specific verification. | Financial/macro series and trade where available. | Requested paths failed with 403/timeout. SBP home page is readable via web retrieval, which does not prove archive/API access. |
| Pakistan Open Data | https://data.gov.pk/ | No CKAN/API assumption; investigate linked applications independently. | Dataset dependent. | Root returned HTTP 404 in direct urllib attempt. https://na.data.gov.pk/ is linked by PBS and accessible via web retrieval. |
| PBS trade dashboard | https://tradedashboard.data.gov.pk/ | Login destination returned by official link; do not bypass. Prefer official external-trade publications. | Country/commodity/time dimensions depend on releases. | Official homepage link redirected to /Home/Login and retrieval returned 502. No trade rows acquired. |
| NEPRA industry reports | https://nepra.org.pk/publications/State%20of%20Industry%20Reports.php | PDF reports plus HTML data repositories for 2022–2025. PDF table extraction requires unit/page verification. | Company, generation technology and annual reporting period; does not imply district economic detail. | Report landing page readable via web retrieval; direct hostname and 2024-25 repository URL returned HTTP 403. Footer all rights reserved. No automatic bulk extract acquired. |
| geoBoundaries geometry | https://www.geoboundaries.org/api/current/gbOpen/PAK/ADM2/ | JSON metadata with pinned GeoJSON/TopoJSON/ZIP links; GeoPandas validation. | Metadata reports districts represented in 2019. | JSON acquired: boundary ID PAK-ADM2-60131773, 126 units, Public Domain source metadata, build 2023-12-12. This is a non-official geometry source (geoBoundaries/Wikipedia), not a PBS 2023 boundary definition. |

## Direct verified publication URLs

- KP province Table 1 Excel: https://www.pbs.gov.pk/wp-content/uploads/2020/07/table_1_kp_province.xlsx — downloaded 33,690 bytes.
- KP district Table 1 Excel: https://www.pbs.gov.pk/wp-content/uploads/2020/07/table_1_kp_districts.xlsx — downloaded 62,461 bytes.
- KP district Table 1 PDF: https://www.pbs.gov.pk/wp-content/uploads/census_tables/tables/table_1_kp_districts.pdf — web reader identifies 9 pages.
- Historical district crops: https://www.pbs.gov.pk/wp-content/uploads/2020/07/area_and_production_by_districts_for_28_years.pdf — 214 pages, 28 fiscal years, food/cash crops.
- Historical indices and growth: https://www.pbs.gov.pk/wp-content/uploads/2020/07/indices_and_growth_rates_historical-1.pdf — 8 pages; indices and published YoY sections.
- Labour participation/unemployment 2024-25 Table 15: https://www.pbs.gov.pk/wp-content/uploads/2020/07/Report-15.pdf — 5 pages.
- NEPRA 2024-25 repository discovered from report page: https://nepra.org.pk/publications/State%20of%20Industry%20Reports/SOI%20Data/List%20of%20Companies%20Genenration%20wise%202024-25%20updated.htm — direct acquisition currently 403.

The `2020/07` upload directory is a storage path, not the dataset reference year. Obtain period/version from the publication contents.

## Measured scale and realistic expansion

The KP XLSX files contain 1,289 and 1,243 stored worksheet row elements respectively. These are **not** statistical record counts: formatting, merged headers, blank and aggregate rows are present. The research script observed 1,608 and 5,954 stored cells respectively; these also are not observations. The pipeline must report counts only after semantic parsing and quarantine/reconciliation.

The Census Excel landing-page HTML contains 304 unique .xlsx links, counted from a successful direct fetch. This is a **file-link count**, not downloaded files or normalized rows. Full-census ingestion requires table-by-table parsers, repeat-header handling and cross-table reconciliation before measuring observation scale.

A published population value of approximately 241 million is people enumerated, not 241 million public records. A survey's households or CPI's markets/items are collection-design figures, not rows available to this platform. Similarly, a portal's advertised series count cannot be multiplied by a uniform history length to claim ingested observations.

The 108 calendar months July 2017–June 2026 across four new-base index measures would provide 432 index observations **if** all parse and validate; this is a transparent potential count, not a measured ingestion result. Published YoY measures can add separate observations without being independent sample periods. Millions may become realistic after permitted SBP bulk-series exports and granular historical trade or microdata are actually acquired; until then the warehouse is engineered for that scale, not benchmarked at that scale.

## Adapter and provenance requirements

Each adapter must retain the original payload unchanged in bronze, hash bytes (SHA256), record URL, retrieval UTC, HTTP status, filename, table/sheet/page, organization, dataset version, period, geography level, licence status and revision state. Store parser version and row identifier on every normalized observation. The source catalog must distinguish `verified_link`, `downloaded`, `parsed`, `blocked`, and `manual_import_required`.

Excel/PDF headers carry units and domain definitions. Keep fiscal years separate from calendar dates, preserve CPI base 2015-16 separately from base 2007-08, and distinguish index, YoY percentage and MoM percentage. Never silently merge revisions. Benchmark extraction and warehouse queries separately.

Geographic joins require explicit aliases and boundary vintage. Report unmatched district names; do not fuzzy-join automatically. Swat can be drilled into only when both matched geometry and source-supported district facts exist. Missing coverage must remain missing. Province/national indicators belong to their own level.

## Licensing and distribution

Open-source software does not automatically open-source third-party data. PBS/NEPRA pages observed all-rights-reserved notices, and a permissive dataset-wide licence was not found in this review. Retain attribution and source links; default downloadable processed-data distribution to disabled where rights are unspecified. Source scripts let researchers reproduce lawful local acquisition, subject to the publisher's conditions. The geoBoundaries API metadata reports Public Domain for this geometry source; retain metadata and attribution and review the exact pinned artifact's licence before distributing. No restricted portal or authentication requirement should be bypassed.
