# Bundled font slot

Place a licensed copy of the requested HYWenHei / 汉仪文黑-85W font here as either:

- `HYWenHei-85W.woff2` (preferred)
- `HYWenHei-85W.ttf`

`webui/static/styles.css` already declares `@font-face` for these filenames and falls back to locally installed HYWenHei, PingFang SC, SF Pro, and system UI fonts if the bundled file is absent.

The repository does not include a Hanyi font binary because that font is proprietary and should only be redistributed with an appropriate license.
