# Brand assets

Icon for the EARLY (Timeular) integration.

| File           | Size    | Purpose                                    |
| -------------- | ------- | ------------------------------------------ |
| `icon.svg`     | vector  | Editable source.                           |
| `icon.png`     | 256×256 | Standard icon.                             |
| `icon@2x.png`  | 512×512 | hDPI icon.                                 |

## Making the icon show up in Home Assistant / HACS

Home Assistant loads integration icons from the central
[`home-assistant/brands`](https://github.com/home-assistant/brands) repository,
**not** from this repo. To get the icon to appear:

1. Fork `home-assistant/brands`.
2. Add these files (this is a custom integration, so it goes under
   `custom_integrations`):
   - `custom_integrations/early/icon.png`  (256×256)
   - `custom_integrations/early/icon@2x.png` (512×512)
3. Open a pull request.
4. Once merged, remove the `ignore: brands` line from
   `.github/workflows/validate.yml` so HACS validation also checks the brand.

Until then, Home Assistant shows a generic placeholder icon, which is expected
for a not-yet-published custom integration.

## Regenerating the PNGs

Edit `icon.svg`, then rasterize to the two required sizes with any SVG
renderer, e.g.:

```bash
rsvg-convert -w 256 -h 256 icon.svg -o icon.png
rsvg-convert -w 512 -h 512 icon.svg -o icon@2x.png
```
