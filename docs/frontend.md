# National statistics application

`apps/web` is a Next.js App Router / React / TypeScript application. It is a source-backed workspace: no synthetic dashboard statistics or mocked values are shipped. If the API is unavailable, a retryable error is shown. If an official source has not been ingested, modules display explicit coverage gaps.

## Run

```sh
cd apps/web
npm ci
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

`NEXT_PUBLIC_API_URL` is a public URL embedded at build time. Do not place credentials in it. The backend must permit the frontend origin via its CORS configuration. For a deployed demo set this to the deployed HTTPS API URL before building.

## Implemented workspace

- National overview shows counts calculated from the warehouse response, source coverage, and source indicator metadata.
- Economy and inflation explorers select official indicators, dates, a comparison series, and raw/index/percentage-change/rolling-mean transformations implemented by the API. ECharts is lazily loaded. The chart supports pan/zoom and data tooltips; the tabular data remains available.
- Domain modules display available trade, population, agriculture, labour, and energy observations without manufacturing unsupported dimensions.
- Catalog and quality views inspect manifests, including available lineage, row counts, and measured quality metrics.
- Models displays persisted forecast artifacts from authentic runs. No forecast or score is shown when no artifact exists.
- CSV export downloads the current response using proper quote escaping. Filtered domain search applies only to loaded rows and is labelled accordingly. Source URL cells open provenance in a new tab.
- TanStack Table provides sortable columns and constrained scrollable tables; API server-side pagination caps domain results. Tables are not virtualized because a page contains only 50 rows.
- Dark/light preference persists locally. Navigation collapses on mobile. Native labelled controls, a skip link, focus outlines and reduced-motion styles support keyboard access.

## Geography boundary policy

MapLibre loads only a configured `NEXT_PUBLIC_BOUNDARY_URL` GeoJSON. The map uses a blank background style and requests no third-party tile service. It renders verified boundaries and allows feature clicks. No boundary bundle is fabricated or included. The selected geography menu contains only values published in the warehouse; national statistics are never assigned to districts. Boundary choropleths require a legally reusable boundary source with stable geographic identifiers and a verified observation join; that integration is not yet implemented. Boundary source, date and licence must be documented before use.

## Design / components

Muted emerald navigation, neutral panels, restrained typography and an information-dense registry differentiate this public statistics product from a sales dashboard. A local shadcn-style Radix Slot Button primitive supports semantic buttons/links; the rest of the controls use native HTML. Tailwind CSS v4 is available alongside explicit CSS tokens to keep the visual system inspectable. ECharts and MapLibre are dynamically imported to avoid eager loading of heavy visual libraries.

## Verification

Node unit tests cover division-by-zero handling, rolling-window completeness and CSV quoting. Playwright tests cover empty-state truthfulness, navigation, theme changes and API-backed selection using explicitly labelled test fixtures. These fixtures exist only in test interception and are not product datasets. Run browser tests after installing Chromium. Production build and TypeScript validation are required in CI.

## Limitations

The frontend does not constitute a deployed live demo until both frontend and API are hosted. Map choropleths, province/division/district hierarchy joins, advanced statistical panels, PDF exports and forecast visualizations need further implementation. Dataset license/download permissions must be enforced by the backend before exposing processed downloads.
