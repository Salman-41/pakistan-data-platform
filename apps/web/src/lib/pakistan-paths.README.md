# Dashboard map geometry

`pakistan-paths.json` contains SVG paths projected from the provincial geometry in [PakData/GISData, PAK_adm1.json](https://github.com/PakData/GISData/blob/master/PAK-GeoJSON/PAK_adm1.json), retrieved 2026-10-03. The upstream attributes identify GADM geometry. Its underlying data rights are separate from this project's code license.

Historical labels are normalized to Balochistan, Sindh, Islamabad, Gilgit-Baltistan and Khyber Pakhtunkhwa. The former FATA polygon is grouped with KP for selection; the original polygon seam remains. This is a province-level overview, not a validated district crosswalk or a statement about disputed boundaries.

The map joins only exact geography names to workspace observations. Census values and dates come from the current report filters. Missing territorial statistics remain unavailable. Population and annual growth layers use `population` and `population_growth_annual`; no national estimate is copied to a province.
