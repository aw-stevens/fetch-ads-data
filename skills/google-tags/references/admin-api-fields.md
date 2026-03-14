# Google Tags / GA4 Admin API Reference

GA4 Admin API v1beta — property configuration queries.

---

## Properties

Uses the same GA4 properties from `~/.fetch-ads-data/config.json` under `google_analytics.properties`.

---

## Actions

### list-streams

Lists data streams (web, Android, iOS) for a property. Shows the Google Tag measurement ID (e.g. `G-XXXXXXXXXX`).

| Column | Description |
|---|---|
| `display_name` | Stream display name |
| `type` | WEB, ANDROID_APP, or IOS_APP |
| `measurement_id` | Google Tag ID (G-XXXXX) for web streams |
| `default_uri` | Default website URL |
| `stream_id` | Numeric stream ID |

### list-key-events

Lists key events (formerly "conversion events") — the events GA4 counts as conversions.

| Column | Description |
|---|---|
| `event_name` | Event name (e.g. `purchase`, `trial_start`) |
| `counting` | ONCE_PER_EVENT or ONCE_PER_SESSION |
| `created` | Date the key event was created |
| `deletable` | Whether the event can be removed |

### list-custom-dimensions

Lists custom dimensions configured on the property.

| Column | Description |
|---|---|
| `parameter_name` | Event/user parameter name used in code |
| `display_name` | Friendly name shown in GA4 UI |
| `scope` | EVENT, USER, or ITEM |
| `description` | Optional description |

### list-custom-metrics

Lists custom metrics configured on the property.

| Column | Description |
|---|---|
| `parameter_name` | Event parameter name |
| `display_name` | Friendly name shown in GA4 UI |
| `scope` | EVENT |
| `unit` | Measurement unit (STANDARD, CURRENCY, MILLISECONDS, SECONDS, etc.) |
| `description` | Optional description |

### list-ads-links

Lists Google Ads accounts linked to the property.

| Column | Description |
|---|---|
| `customer_id` | Google Ads customer ID |
| `ads_personalization` | Whether ads personalization is enabled |
| `link_id` | Internal link ID |

---

## Common Use Cases

- **"What tags do we have?"** → `list-streams` shows all measurement IDs
- **"What are our conversion events?"** → `list-key-events`
- **"What custom dimensions are set up?"** → `list-custom-dimensions`
- **"Is our Google Ads account linked?"** → `list-ads-links`
- **"Audit our GA4 configuration"** → Run all actions for the property
