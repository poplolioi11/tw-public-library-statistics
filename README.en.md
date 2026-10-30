# Taiwan Public Library Statistics Across Years

[完整中文說明](README.md#完整中文說明) · [Open the chart explorer](https://poplolioi11.github.io/tw-public-library-statistics/) · [Download v0.9.1](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1)

This is an English translation and navigation guide to the existing Chinese documentation. It adds no new statistical observations, review certification, or dataset version. Consult the Chinese documentation for exact source terminology and original quotations.

[![Data and code checks](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml/badge.svg)](https://github.com/poplolioi11/tw-public-library-statistics/actions/workflows/check.yml)

Explore Taiwan's public-library collections, circulation, library counts, and service statistics, and trace each value to its official source. View charts directly, or download data for spreadsheet tools, programs, or AI-assisted analysis.

## Start with three common questions

| What would you like to find out? | Start here |
| --- | --- |
| How has national book circulation changed in recent years? | [View the 2020–2024 book-loan chart](https://poplolioi11.github.io/tw-public-library-statistics/?profile=national-ncl-book-loans-panel&from=2020&to=2024). It uses one checked panel from the original publications, with a route back to the official source for each value. |
| Where are historical county/city library counts or monthly branch tables? | [Explore county/city library counts under the DGBAS definition](https://poplolioi11.github.io/tw-public-library-statistics/?profile=county-library-count-dgbas&entity=%E8%87%BA%E5%8D%97%E5%B8%82), or [view a monthly branch-table example for Sanmin Branch](https://poplolioi11.github.io/tw-public-library-statistics/?profile=discovered-official-monthly-tables&series=comparison-9d8764a5d362caefbadaac33). |
| How can I analyze the data myself or use it with AI? | Download [CSV](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/observations.csv), [JSONL.gz](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/observations.jsonl.gz), or [SQLite](https://github.com/poplolioi11/tw-public-library-statistics/releases/download/v0.9.1/library_statistics.sqlite). For smaller files, use the [annual index](data/by_year/index.json). See the [AI and analysis guide](AI_USAGE.md) for reading instructions. |

**Before use:** historical gaps remain, definitions differ between some sources, and transcriptions of scanned yearbooks have not undergone independent human double-checking. See [coverage and gaps](COVERAGE.md) and the [comparison rules](README.md#比較前先確認口徑) for the boundaries of the charts and source-reported values.

Documentation status checked on **2026-10-30**; the dataset remains **v0.9.1**. **Human sample reading and independent human double-checking are not yet complete.** No human reference readings, error rates, or model accuracy scores have been filled in ahead of that work. Code checks, source hashes, and AI review against source images do not replace human reference data. The [source backlog and completed scope](docs/source-backlog.md) are recorded separately; use [CITATION.cff](CITATION.cff) for the versioned citation.

## Version, citation, and method

Version **0.9.1**; data build date **2026-10-29**. Public repository: [poplolioi11/tw-public-library-statistics](https://github.com/poplolioi11/tw-public-library-statistics). [Download v0.9.1](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1).

Use **Cite this repository** in the repository sidebar or [CITATION.cff](CITATION.cff), and record the version, selected statistical definitions, and official source tables used in your work. Version v0.9.1 was archived on Zenodo on 2026-10-30 with version DOI [10.5281/zenodo.23788194](https://doi.org/10.5281/zenodo.23788194). The fixed GitHub Release continues to identify the original public version.

The [data-paper draft on sources, methods, validation, and limitations](docs/DATA_PAPER_DRAFT.md) is **an unsubmitted draft that has not been peer reviewed**. [Reuse evidence and feedback](docs/REUSE.md) explains how to report actual use. Stars, forks, and download counts are not treated as direct evidence of research adoption.

Compiled and maintained by **Chu, Chen-Yu (曲宸宇)**; GitHub: [poplolioi11](https://github.com/poplolioi11); [ORCID](https://orcid.org/0009-0003-9738-6914). The Chinese name, English name, and account identify one author. Authorship and rights in official statistics remain those of each source.

Existing work was checked before compilation. The National Library of Public Information already provides charts across years; the National Central Library has a statistical terminology dictionary; SEGIS and local open-data services also contain related historical work. This project's contribution is **a consistent way to read multiple sources, record-level source locations, period and definition annotations, and traceable content versions**. It does not claim to be the first collection of statistics across years or the first terminology dictionary. See the [prior-work review](research/prior-art.md) and [official scope and definitions](research/official-scope.md).

## What is included

The current dataset contains **58,245 source-observation records**, including **206 explicitly missing cells**, **1,303 cells left blank in the original publications**, **5,413 cells containing original textual statuses**, and different publication versions. A record count is not a count of libraries, and the entire dataset must not be summed as one total.

| Source family | Compiled scope | Records |
| --- | --- | ---: |
| National Library of Public Information: public national charts | Public national charts for 2011–2025; national figures only | 855 |
| National Library of Public Information: 2023 open data, including counties/cities | The 2023 annual resources with an explicit OGDL statement; national, county/city, and alternative definitions remain separate and are not added together | 2,236 |
| National Central Library yearbook statistical facts | Specified core tables, public-library subsets, and original figures in volumes 91–114; data years 2001–2024; different publication versions retained | 20,795 |
| National Central Library reading-report statistical facts | 5 national reading-report tables for 2011–2012, including comparisons across years; not county/city tables | 154 |
| DGBAS historical national statistics | 3 source versions; data years 1991–2011; overlapping versions kept separately | 220 |
| DGBAS county/city public-library counts | Officially recast geographic units for 1998–2025; the source includes the National Central Library; missing values are not filled with 0 | 644 |
| Local-government historical open tables | Confirmed series for Hsinchu City and Taichung City; original annual/monthly periods and collection locations retained | 14,751 |
| Later DGBAS national published statistics | Table 4-22 in the ROC year 113 statistical yearbook, covering 2010–2024; national figures include the National Central Library; agency and county/city rows without individually stated years remain unknown | 312 |
| Local official published statistical facts | The listed publications for New Taipei, Tainan, Taoyuan, Changhua, Kaohsiung, and Taipei, 2006–2021; national/county-city/district/branch and annual/monthly figures remain separate; unstated years are stored separately | 18,230 |
| Ministry of Education historical public-library statistics | The social-education table 3 for the nearly 16-year period 1994–2009; includes the National Central Library; units are thousand volumes/thousand visits; not added to overlapping publication versions | 48 |

For batch-level cell counts, data years, editions, and the exact tables or original-text scope, see the [reviewed historical batches](docs/historical-batches.md) and [COVERAGE.md](COVERAGE.md).

The 2012 originals list per-capita book-acquisition, book-ownership, and borrowing ratios for 22/22/22 counties and cities respectively. Population served per librarian is listed for only 21 counties/cities; Lienchiang County is absent. The core original-quantity table for all 22 counties/cities has not been obtained and must not be reconstructed from ratios. The reading-report tables contain national aggregates only and must not be presented as county/city tables.

Some county/city labels in the 2015 original publication remain unresolved: two rows both print Kinmen. The dataset retains 183 observations with uncertain geographic labels rather than replacing one with Lienchiang or forcing a match to current boundaries. Other geographic-label uncertainties are listed by data year: 36 cells for 2024. Their printed names and values are preserved, and these cells do not count as confirmed county/city coverage.

In 2015 table 17, the heading “場次” conflicts with the body text “人次”. The units of 161 cells remain null, with `source_heading_conflict_unresolved`; “人次” is only a `unit_interpretation_candidate`, not a confirmed unit. Other conflicts between headings and the counting basis in the body affect 51 cells for 2005. Their `unit` remains blank; original units and source references are stored separately, and the cells are not treated as straightforward book-volume counts. Where the distinction between persons and person-visits remains unresolved, `unit=null` is retained: 3 cells for 2005 and 23 for 2016. `unit_raw` retains the original heading.

**Completeness means the full confirmed tables/resources from the listed sources, not complete coverage of all counties/cities and all historical years in Taiwan.** The overall reference-year range is 1991–2026, but available indicators, geography, and definitions differ by year. This range is not a continuous, consistently defined nationwide county/city panel. Materials not obtained, not parsed, or without confirmed rights are listed as gaps; a gap does not mean the official source has no data.

The 26 rows for 2023 comprise a national total, 22 counties/cities, and 3 alternative definitions excluding national libraries for New Taipei, Taichung, and Nantou. They are not 26 counties/cities. In local data, Hsinchu includes every month of ROC years 105–114, months 1–8 of ROC year 115, and December of ROC year 104. Taichung annual reports, monthly reports, branch circulation, and book-acquisition data retain their original periods. See [coverage and gaps](COVERAGE.md), the [source-coverage list](data/combined/coverage.json), the [current summary](data/combined/summary.json), and the [local historical-data review](research/local-history.md).

The DGBAS county/city library-count series contains **28 years × 23 rows = 644 cells**. All entries for 1998–2005 are explicitly missing as `-`, totaling 184 cells. The 2006–2025 period has 460 numeric cells, including each year's national total. The source uses the official post-reorganization county/city classification: the historical values for 2006–2010 have also been officially recast into the 22 current counties/cities. This was not a merge performed by this project. The source's current definition includes **the National Central Library, the National Library of Public Information, and the National Taiwan Library**. Its population differs from the National Library of Public Information's public-library counts. The two series must not be used to fill each other's missing years or joined into a series with one assumed definition. The applicability of the definitions has not been independently certified year by year.

For this series, consult the [official query page](https://winstacity.dgbas.gov.tw/DgbasWeb/ZWeb/StateFile_ZWeb.aspx?Type=table), the [JSON recording original source cells](raw/segis-history/dgbas_county_original_cells.json), or the [reproduction script using the normal public-form POST](scripts/fetch_segis_history.py). Original HTML is not included in the public package.

## Download and read the data

[Version and complete downloads](https://github.com/poplolioi11/tw-public-library-statistics/releases/tag/v0.9.1) · [Read JSONL by year](data/by_year/index.json)

The public copies remove unrelated contact fields from 22 original files and provide statistical projections with separate hashes. Original source URLs, source-file SHA hashes, and every statistical value are retained. See [the distinction between public copies and source originals](docs/PUBLICATION.md).

## Reading entry points

- [Public lightweight chart explorer](https://poplolioi11.github.io/tw-public-library-statistics/): browse directly, share query URLs, and follow each record back to its official source.
- [Line charts and question-based source selection](site/phase3.html#line-charts); [all original-publication series](site/phase2.html#line-charts); [record-level original values](site/index.html).
- [JSONL](data/combined/observations.jsonl.gz): one complete observation per line, suitable for programs and AI-assisted work.
- [CSV](data/combined/observations.csv.gz): the same formal observations, suitable for spreadsheet tools.
- [SQLite](data/combined/library_statistics.sqlite.gz): the same formal observations; the table is named `observations`.
- [Observation schema](data/combined/observation.schema.json), [indicator list](data/combined/indicators.json), and [data-package descriptor](datapackage.json).
- [AI and analysis instructions](AI_USAGE.md), [rights and licenses](LICENSE.md), [machine-readable entry point](llms.txt), and [supplementary documentation](docs/).

**For analysis, use only the three observation-file formats listed above in `data/combined/`.** `data/observations.*`, `data/component_records.jsonl`, and `derived/` are source components or intermediate observations. They can contain duplicates and must not be appended to the formal observations.

## Check definitions before comparing

Each record preserves its source URL, original page/table/row/column location, SHA-256, retrieval time, source and publication versions, and the data period, unit, population, and geographic scope that could be confirmed. Unknowns stay unknown; current definitions are not backfilled into all earlier years.

First choose a `source_family` or `source_id`. Before comparing, check `series_id`, `geographic_scope`, `national_libraries_scope`, `temporal_kind`, `period_basis`, `unit`, `source_edition`, and the notes.

- National totals, county/city figures, national-library figures, and rows including/excluding national libraries can overlap. Do not sum the whole table.
- Monthly flows are not automatically annual totals. Year-end stocks, annual additions, and circulation flows also measure different things.
- Historical source tables, including those from the National Central Library, retain names such as the former Taipei County and Taichung County/City. The DGBAS county/city library-count series instead uses officially recast geography. Check `geography_vintage`; do not treat these geographic definitions as identical or merge them again yourself.
- Read `value=null` together with `value_status`: `source_blank` means the original publication left the cell blank; `not_available_in_source` means explicit missingness; `source_marker` preserves printed text such as “無” or “未新增”. None is automatically zero or not applicable. A source-reported `0` remains the reported value; consult `zero_interpretation` rather than assuming it proves a true zero or a complete survey.
- Person-visits are not unique people. Collection locations can be reading rooms or small library service points and must not be converted directly into counts of physical libraries. Ratios must not be added across geographic areas.

Faithful transcription and successful checks do not prove that the original statistical reporting is correct. The local sources contain 28 identified arithmetic inconsistencies in totals, and National Central Library yearbooks also have internal discrepancies. Original values are preserved. Read `quality_flags`, `notes`, and the [quality review](derived/local_historical_quality.json).

## Sources, rights, and reproducibility

The source-expansion research snapshot is documented in the [2026-10-28 research report](research/source-discovery-20261028.md) and [candidate list](docs/source-discovery-20261028.json): 16 originals were obtained at that time and another 396 cells were checked. This is a historical record from before ingestion. Version v0.9.0 subsequently incorporated the complete specified tables from 12 originals; see the [official-table ingestion batch](README.md#2026-10-28官方原表入庫批次). Research probes are not counted again as formal data. The core original quantities for all 22 counties/cities in 2012 remain missing.

The 2023 and local open data explicitly state OGDL version 1. DGBAS historical tables are recorded under the relevant official open-data statement. Applicability to the DGBAS county/city query subsite is inferred from the parent site's broad statement and marked `license_scope_inference=true`; no separate terms were found on the subsite, so this is not represented as an independent license grant by that subsite. This project compiles public statistical facts from National Central Library yearbooks and public charts. It does not claim that full chapters, PDFs, or original HTML/JavaScript are open content. NCL PDFs and original website HTML/JS are no longer redistributed in the public package. See [LICENSE.md](LICENSE.md) for attribution and rights categories.

The National Library of Public Information's [2026-09-17 notice](https://publibstat.nlpi.edu.tw/Frontend/News/ShareNewsView?NewsID=News000050) separately governs the current public scope and the uses of data obtained by application. Existing versions with explicit open terms and newly requested data must be handled separately. A license in an older catalog is not used to infer that other years or requested data may be republished.

Source groups, content-hash caches, source versions, and update scripts are provided. The main update entry point is [`scripts/run_update.py`](scripts/run_update.py); source and parsing review records are in [research/](research/). Scripts and source conditions are governed by their current versions. Identical content retains its first retrieval time, while recheck times are recorded separately. If an update fails, the previous verifiable version is retained and its status is marked. Maintenance checks occur monthly; no-change checks remain quiet, and significant additions, revisions, or failures prompt notification. Private scheduling settings are not included in the public package and are not enabled by downloading it.

When reproducing an analysis, record this project's version, `observation_id`, source `source_id`/`source_sha256`, and the selected definitions. Preserve versions when changing tables; do not overwrite original source values.

## Run updates and reproduce the build

Analyzing the existing data does not require downloading sources or installing packages. The update environment requires Python 3.12 and the packages listed in `requirements.txt`; run `python scripts/run_update.py`. The project records one completed local end-to-end validation and a second run with unchanged data.

The public package deliberately excludes original PDFs and complete web pages. To redo PDF extraction and full source validation, first run `python scripts/restore_originals.py`. It fetches only the explicitly listed official URLs and checks the specified SHA hashes; a changed original stops the process for review. Then run `python scripts/run_update.py --offline`. Reconstruction preserves original values and explicit missingness; it does not fill gaps with estimates. If chart pages or policy pages have changed, review the source menus and new notices before accepting a new version.

## Phase 1: nationwide source and gap inventory

Phase 1 completed source navigation, an inventory of original definitions, and the acquired source batches for 2005–2025. It does not claim that all historical values throughout Taiwan are complete.

- The current 22 counties/cities × 4 agency roles give 88 entries with actual check records. This does not mean every agency archive was exhausted. The 440 candidates distinguish entry points, failed downloads, items awaiting parsing, and completed attachments.
- The 4,830 “year × navigation area × topic” cells in the Phase 1 snapshot show source availability. The 29,337 groups with exact original definitions retain the 37,887 observations present at that time; distinct original geographies, populations, units, periods, and versions are not merged.
- Additions include all 119 rows/123 quantity cells from 2005 plan tables 6/7, and 18,486 statistical cells from 4 Hualien/Lienchiang attachments. Another 33,705 source cells in the permitted scope include headings and structural blanks. These are different views: they must not be added together, and they were not mixed into the existing formal observations.
- Each of the two Hualien ODS files retains 72 monthly worksheets, from September 2020 to August 2026, plus blank templates. Conflicting year/month information in 176 cells remains unknown. The Lienchiang attachment listed under ROC year 113 does not print a year and is kept separately from the source whose worksheet explicitly prints ROC year 114.

[Interactive source and gap page](site/phase1.html) · [Scope and validation](docs/PHASE1.md) · [Supplementary sources](docs/phase1-supplements.md) · [Small worksheet partitions](docs/phase1-source-cell-partitions.json) · [Machine-readable dictionary](docs/phase1-data-dictionary.json)

The 2012 county/city core original quantities have still not been obtained and are not reconstructed from ratios. Phase 2 adds record-level definitions and limited comparison rules supported by original publications. Full certification of historical methods has not been established. Phase 3 provides bounded default source selection; see [docs/PHASE3.md](docs/PHASE3.md).

## Phase 2: source-supported review of statistical definitions

Version v0.9.1 reviews the existing 76,854 quantitative records individually: 58,245 formal observations, 18,486 local source cells, and 123 plan quantity cells. The three layers remain separate and are not added into a measure of library activity. There are 445 source evidence cards and 100 breakpoint/field rules that link to official originals, SHA hashes, and source-table positions.

- Within the scope of the original publications/files, 1,677 groups support limited comparisons over multiple periods; 554 involve different years. This is not certification of a common method, complete historical coverage, or a panel across sources.
- The number of originally null-unit records eligible for an additional interpretation from the verified original “冊數／人次” headings is 0. The 14,400 original five-digit year/month strings are decoded strictly. Original values, `unit`, and `data_year` remain unchanged.
- Unresolved definitions, effective years, units, geography, and periods remain in the reason fields. Matching labels, identical numbers, a shared table, or the publication year of a contemporary standard do not by themselves establish an unchanged method across historical years. The 2012 original-quantity gap is not estimated.

[Interactive definitions and sources](site/phase2.html) · [Phase 2 documentation](docs/PHASE2.md) · [Record-level JSONL, gzip](derived/phase2/annotations.jsonl.gz) · [Record-level CSV, gzip](derived/phase2/annotations.csv.gz) · [SQLite](derived/phase2/definitions.sqlite) · [Small files by layer/year](docs/phase2-partitions.json)

## Phase 3: choose sources by question and view line charts

Version v0.9.1 provides 22 preset questions with explicit populations and purposes. They route all 76,854 existing quantitative records and retain 115,356 candidate decisions with source-selection reasons. These are source-selection annotations, not additional library counts or operating volumes; original statistical values remain unchanged.

[Line charts and source selection](site/phase3.html#line-charts) · [All original-publication series](site/phase2.html#line-charts) · [Question index](docs/phase3-question-index.json) · [Scope and usage](docs/PHASE3.md) · [Small files by question/year](docs/phase3-partitions.json)

The main entry point directly displays the checked National Central Library book-circulation series from original publications. Phase 2 contains 1677 checked series charts. Phase 3 contains 2767 charts of original series within questions and 847 interval results precomputed by the same Python source selector. Reported points link back to official sources. Missing values, missing periods, and changes in definition are not joined by chart lines.

Source selection and comparability across years are separate decisions: a record marked `selected` can still be missing or unusable. Edition priority is a maintainer policy; other versions are retained. The complete core original-quantity table for all 22 counties/cities in 2012 remains missing. A few acquired original branch/reading-room components are preserved without presenting them as the complete core quantities.

## Official-table ingestion batch of 2026-10-28

Version v0.9.1 retains the 20,358 original cells ingested on 2026-10-28 from the complete specified tables and continuation pages of 12 official originals. They are not observations added by this metadata revision. Early yearbooks for 2001–2004, Ministry of Education data for 1994–2009, national DGBAS tables for 2010–2024, and the listed publications from New Taipei, Tainan, Taoyuan, Changhua, Kaohsiung, and Taipei are stored separately. Kaohsiung includes all 52 pages of table 3-2, with annual and 12 monthly values for each library. Taipei's scope in this batch is December 2012 only.

The added cells comprise 14,540 numeric cells, 427 original publication blanks, and 5,391 original symbols/composite cells. The periods of 467 cells remain unconfirmed. A count of source cells is not a count of libraries. Totals, components, annual totals, and monthly values must not all be added together. An unknown original year is not replaced with its publication year; missing source values are not filled with 0. New Taipei collection figures are segmented around 2010. Kaohsiung's definitions for annual collection/periodical aggregates and circulation rates remain unresolved and are not treated as a trend in year-end stock.

The [complete source/table scope](raw/discovered-20261028/extraction-metadata.json) and [record-level source-cell validation](scripts/validate_discovered_20261028.py) can be rerun. Each cell retains the original string, unit, official source URL, SHA, original page/table/row/column position, version, and formula/denominator. Reading the JSON in `source_time_reference` gives additional source-specific context, including merged cells and formulas; `source_cell_note_raw` preserves the review method. The 369 scanned cells were read using Apple Vision and AI review against original images. This is not a claim of human double-checking for every character or cell. Repeated OCR is not an independent engine.

The original discovery register and 396 research-probe cells are a v0.8 historical snapshot, not extra observations. Formal mappings are recorded in this batch's metadata and `derived/discovered_20261028_observations.jsonl.gz`. The Taipei 2012 yearbook rights conflict and the pending-review subsets of three statistical chapters spanning multiple library types remain isolated. Complete core original quantities for all 22 counties/cities in 2012 are still missing: they are neither estimated from ratios nor assembled into a purported nationwide panel by combining sources.

The 16 composite/non-scalar source cells are individually registered in `scripts/reviewed_non_scalar_literals.json`, including original-file SHA, original text, and location. A main-library figure with a branch count in parentheses, “各1人”, or “每鄉各2” cannot be reduced to an arbitrarily chosen number and called a total. For these cells, `source_marker` and `selected_source_missing` mean there is no single usable scalar; they do not mean that the original contains no data. Read `raw_value`, the original note, and the register together. Do not estimate replacement values.

Monthly maintenance continues. Newly added fixed historical originals become due for rechecking every 365 days. If the source and extractor are unchanged, the complete batch is reused. Changed originals are held pending review, and a failure retains the previous version. Newly downloaded material is not automatically treated as licensed for publication.

## v0.9.1: unit and source-location revisions

Using fixed originals, units were confirmed for 14,596 records: 14,584 from original local column headings and 12 from national electronic-resource totals in the same volume. Missing units fell from 16,286 to 1,690. Values, original strings, missing-value states, identifiers, and periods are unchanged. The 467 records with missing years were reviewed group by group and retain unknown or cross-year status. The source summary for volume 91 now includes the continuation table on page 5. **Human double-checking is still incomplete.** The 2012 core original-quantity gap is not estimated. See the [record-level revisions and unresolved items](docs/metadata-review-20261029.md).

## Public lightweight chart explorer

[Open the charts](https://poplolioi11.github.io/tw-public-library-statistics/). There is no need to download an entire HTML document: the site first loads the question catalog, then small JSON files for the selected series. Mobile axis labels use a fixed font size. Each plotted point and table value links back to the official original or official dynamic query entry point, with the source-file SHA, original table position, and edition.

The data version remains **v0.9.1**; the viewer has its own version, **v1.0.0**. The existing 1677 original-publication series, 2767 within-question series, and 847 precomputed intervals are exported in full. The same original series may occur in multiple questions; these counts must not be added together as statistical observations. Only presentation and transfer have changed: original values, missingness, definitions, source selection, and permitted line segments are unchanged. For single-period facts or questions without eligible charts, consult the full data package. Having no chart does not mean there are no data.

See the [site scope, rebuild, and validation](docs/LIGHTWEIGHT_SITE.md). The existing single-file viewers remain available for offline use; GitHub Pages deploys only `site/light/`.

Complete CSV and SQLite files are provided with lossless gzip compression. Decompress them for use with ordinary CSV/SQLite tools; the Release also provides the same decompressed files. `record_io` reads JSONL/CSV automatically according to the publication profile. SQLite validation checks a temporary decompressed file. Statistical values, SQL NULLs, and source locations are unchanged by compression.
