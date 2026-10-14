# Manifest format

A manifest follows [`schema/manifest.schema.json`](schema/manifest.schema.json). [`site/trending/manifest.json`](site/trending/manifest.json) is a complete example.

## Top level

- `id`, `name`, `version` and `types` are required. `version` is `MAJOR.MINOR.PATCH`.
- `id` is a lowercase reverse-domain name under `sh.thirdshift.`.
- `resources` may list `meta` or `subtitles` but never `stream` or `catalog`. `catalogs` stays empty.
- `behaviorHints.adult` and `behaviorHints.p2p` can only be `false`.
- Unknown keys and repeated JSON keys are refused.

## `specula`

### `homeRows`

Rows on the Home screen. Each has an `id`, a `title` and a `query`.

| Query field | Values |
| --- | --- |
| `kind` | `trending` or `popular` |
| `media` | `movie`, `series` or `all` |
| `window` | `day` or `week` |
| `count` | 1 to 20 |
| `options` | Maps `kind`, `media`, `window` or `providers` to the key of an option that sets it |

### `options.fields`

Settings shown to the user. Each has a `key`, a `title` and a `kind`. A `footnote` and a `defaultValue` are optional.

| Kind | Rules |
| --- | --- |
| `text` | Optional `placeholder` |
| `secret` | No default |
| `toggle` | |
| `choice` | `value` and `label` pairs with unique values. The default must be one of them. Mapped to a query field, its values must be ones that field accepts |
| `metadataProviders` | Names the row it fills. The only kind that can be mapped to `providers` |

### `menuItems`

Actions in the player menu: `fetchSubtitles` or `listAlternativeStreams`. Each has an `id`, a `title` and an `action`.

### `attribution`

`id`, `name` and `text` are required. `version`, `url` and `logo` are optional.
