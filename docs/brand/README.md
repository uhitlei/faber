# Faber brand

The mark is a kitsune, the nine-tailed fox of Japanese folklore, cut into
horizontal slices that shift sideways like a scanline glitch. Nine gates,
nine tails; the slices are the gates the fox passes through.

## Files

| File | Use |
|---|---|
| `faber-mark.svg` | dark backgrounds (amber + off-white accents) |
| `faber-mark-light.svg` | light backgrounds (amber + ink accents) |
| `faber-mark-{512,256,128,64,32}.png` | raster, dark-background colours, transparent |
| `faber-mark-light-{512,256,128,64,32}.png` | raster, light-background colours, transparent |

The SVGs are square, have a transparent background, and cut the ear and the
eye out with a mask, so they sit on any colour.

## Colours

| Token | Hex | Role |
|---|---|---|
| amber | `#f2b53a` | the fox; also the colour of the human gates in the docs |
| off-white | `#e3e8e2` | accents on dark backgrounds |
| ink | `#142029` | accents on light backgrounds |
| charcoal | `#0e151a` | the dark ground used in the presentation |

Wordmark: **Big Shoulders Display 900**, uppercase. Captions: IBM Plex Mono.

## In a README

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/faber-mark.svg">
  <img src="docs/brand/faber-mark-light.svg" alt="Faber" width="200">
</picture>
```
