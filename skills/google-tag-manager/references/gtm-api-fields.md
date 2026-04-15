# Google Tag Manager API Reference

Tag Manager API v2 — container configuration queries.

---

## GTM Hierarchy

```
Account
  └── Container (has a public ID like GTM-XXXXX)
        └── Workspace (usually "Default Workspace")
              ├── Tags
              ├── Triggers
              ├── Variables
              ├── Built-in Variables
              └── Folders
```

Most queries need account + container + workspace. Workspace is auto-detected if not specified.

---

## Actions

### list-containers

Lists containers in a GTM account.

| Column | Description |
|---|---|
| `container_id` | Numeric container ID (used in API) |
| `name` | Container display name |
| `public_id` | Public GTM ID (e.g. GTM-XXXXX) |
| `usage_context` | web, server, iosFirebase, androidFirebase |

### list-workspaces

Lists workspaces in a container.

| Column | Description |
|---|---|
| `workspace_id` | Workspace ID |
| `name` | Workspace name |
| `description` | Workspace description |

### list-tags

Lists all tags in the workspace, with trigger names resolved from IDs.

| Column | Description |
|---|---|
| `tag_id` | Tag ID |
| `name` | Tag display name |
| `type` | Tag type code (see Common Tag Types below) |
| `firing_triggers` | Comma-separated trigger names that fire this tag |
| `blocking_triggers` | Comma-separated trigger names that block this tag |
| `paused` | Whether the tag is paused |
| `measurement_id` | GA4 measurement ID (when applicable) |

### list-triggers

Lists all triggers in the workspace.

| Column | Description |
|---|---|
| `trigger_id` | Trigger ID |
| `name` | Trigger display name |
| `type` | Trigger type code (see Common Trigger Types below) |
| `filter` | Brief summary of filter conditions |

### list-variables

Lists custom variables in the workspace.

| Column | Description |
|---|---|
| `variable_id` | Variable ID |
| `name` | Variable display name |
| `type` | Variable type code (see Common Variable Types below) |

### list-built-in-variables

Lists enabled built-in variables.

| Column | Description |
|---|---|
| `name` | Variable name |
| `type` | Variable type |

### list-folders

Lists tag folders (used to organize tags).

| Column | Description |
|---|---|
| `folder_id` | Folder ID |
| `name` | Folder name |

### get-version

Shows the currently published (live) container version.

| Column | Description |
|---|---|
| `version` | Version number |
| `name` | Version name |
| `description` | Version description |
| `fingerprint` | Version fingerprint |
| `tag_count` | Number of tags in this version |
| `trigger_count` | Number of triggers |
| `variable_count` | Number of variables |

---

## Common Tag Types

| Type Code | Description |
|---|---|
| `gaawe` | GA4 Event tag |
| `gaawc` | GA4 Configuration tag |
| `html` | Custom HTML |
| `img` | Custom Image (pixel) |
| `awct` | Google Ads Conversion Tracking |
| `sp` | Google Ads Remarketing |
| `gclidw` | Conversion Linker |
| `flc` | Floodlight Counter |
| `fls` | Floodlight Sales |
| `hjtc` | Hotjar Tracking Code |
| `sdl` | Scroll Depth Listener (legacy) |

---

## Common Trigger Types

| Type Code | Description |
|---|---|
| `pageview` | Page View (DOM Ready, Window Loaded, etc.) |
| `click` | Click — All Elements |
| `linkClick` | Click — Just Links |
| `customEvent` | Custom Event |
| `formSubmission` | Form Submission |
| `jsError` | JavaScript Error |
| `timer` | Timer |
| `scrollDepth` | Scroll Depth |
| `youtubeVideo` | YouTube Video |
| `elementVisibility` | Element Visibility |
| `historyChange` | History Change |
| `triggerGroup` | Trigger Group |
| `always` | Initialization — All Pages |
| `consentInit` | Consent Initialization |

---

## Common Variable Types

| Type Code | Description |
|---|---|
| `v` | Data Layer Variable |
| `jsm` | Custom JavaScript |
| `j` | JavaScript Variable (global) |
| `d` | DOM Element |
| `c` | Constant |
| `k` | First Party Cookie |
| `u` | URL |
| `gas` | Google Analytics Settings |
| `gtes` | Google Tag: Event Settings |
| `remm` | Regex Table |
| `smm` | Lookup Table |

---

## Common Use Cases

- **"What tags are deployed?"** → `list-tags`
- **"What triggers fire the GA4 tag?"** → `list-tags` (shows firing_triggers column)
- **"What custom events are we tracking?"** → `list-triggers` (filter for customEvent type)
- **"What variables are configured?"** → `list-variables`
- **"What version is live?"** → `get-version`
- **"Audit the full GTM container"** → Run `list-tags`, `list-triggers`, `list-variables`
