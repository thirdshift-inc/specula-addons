# specula-addons

First-party add-on manifests for Specula, a video player for Apple platforms, visionOS-first.

[Manifest format](manifest-format.md) · [Schema](schema/manifest.schema.json)

## Add-ons

| Add-on | Id | Manifest |
| --- | --- | --- |
| Trending | `sh.thirdshift.specula.trending` | https://thirdshift-inc.github.io/specula-addons/trending/manifest.json |

Trending adds a Home row of trending films and series filled by the metadata providers set up in Specula.

First-party add-ons describe what Specula draws. They serve no streams and no catalogues.

## Writing a manifest

Put it at `site/<name>/manifest.json` and it is served at `https://thirdshift-inc.github.io/specula-addons/<name>/manifest.json`. The rules are in [Manifest format](manifest-format.md).

## Validating

Python 3.12 with no dependencies:

```sh
python -m unittest -v
python -m addon_manifest.validate site
```

## Publishing

Changes reach `main` through pull requests checked by CI. A push to `main` runs the same checks and publishes `site/` to GitHub Pages. If a check fails nothing is published.

## Licence

MIT, copyright (c) 2026 thirdshift-inc. See [LICENSE](LICENSE).
