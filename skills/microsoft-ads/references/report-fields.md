# Microsoft Advertising — Report Fields Reference

The query tool wraps the Microsoft Advertising **REST Reporting API** (v13). It submits a
performance report (`POST …/Reporting/v13/GenerateReport/Submit`), polls until ready
(`…/GenerateReport/Poll`), downloads the zipped CSV from the pre-signed URL, and prints the rows.

Docs: https://learn.microsoft.com/en-us/advertising/guides/reports?view=bingads-13

## Report types (`--report-type`)

| Value | Report | Rows are… |
|-------|--------|-----------|
| `campaign` (default) | CampaignPerformanceReport | one row per campaign (× time bucket) |
| `account` | AccountPerformanceReport | one row per account (× time bucket) |

## Aggregation (`--aggregation`)

`Summary` (default — one row per entity for the whole range), `Daily`, `Weekly`,
`Monthly`, `Yearly`. The `TimePeriod` column is only meaningful for non-Summary
aggregations and is dropped automatically when `--aggregation Summary`.

## Date range (`--start` / `--end`)

`YYYY-MM-DD`, or shorthand `today`, `yesterday`, `7daysAgo`, `30daysAgo`, `90daysAgo`.
Reports use a custom date range built from these.

## Default columns

**campaign**: `TimePeriod`, `AccountName`, `AccountId`, `CampaignName`, `CampaignId`,
`CurrencyCode`, `Impressions`, `Clicks`, `Spend`, `Conversions`

**account**: `TimePeriod`, `AccountName`, `AccountId`, `CurrencyCode`, `Impressions`,
`Clicks`, `Spend`, `Conversions`

Override with `--columns` (comma-separated). Common additional columns:

| Column | Meaning |
|--------|---------|
| `Ctr` | Click-through rate |
| `AverageCpc` | Average cost per click |
| `Conversions` | Conversions (per the account's conversion goals) |
| `ConversionRate` | Conversion rate |
| `CostPerConversion` | Cost per conversion |
| `Revenue` | Revenue attributed to conversions |
| `Spend` | Cost / spend in account currency |
| `CurrencyCode` | Account currency (e.g. USD) |
| `DeviceType` | Device segmentation |
| `CampaignStatus` / `AccountStatus` | Entity status |

Full column value sets:
- CampaignPerformanceReportColumn: https://learn.microsoft.com/en-us/advertising/reporting-service/campaignperformancereportcolumn?view=bingads-13
- AccountPerformanceReportColumn: https://learn.microsoft.com/en-us/advertising/reporting-service/accountperformancereportcolumn?view=bingads-13

## Notes

- **Conversions** require conversion goals (UET tags) configured in the account; otherwise
  the column returns 0.
- **Spend** is in the account's currency (`CurrencyCode`).
- Values are returned as strings exactly as Microsoft formats them (matching the other
  query tools); `--format json`/`csv` preserve them verbatim.
