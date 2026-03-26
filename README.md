# sota-om-summits

Nature protection level database for all **379 Slovak (OM) SOTA summits**, helping ham radio operators determine which summits are safe to activate under Slovak nature protection law.

🌐 **[Live demo →](https://trgosk.github.io/sota-om-summits/)**

![screenshot](screenshot.png)

## Why?

Slovakia has 5 levels of nature protection (*stupne ochrany*). Operating a radio station in level 5 areas may be considered disturbing peace and quiet — which is explicitly prohibited. Many SOTA summits fall inside National Parks (level 3), nature reserves (level 4–5), or have specific trail closures.

This tool maps every OM summit to its protection level so you can plan activations responsibly.

## Protection levels at a glance

| Level | Territory | SOTA impact |
|-------|-----------|-------------|
| **1** | General (whole Slovakia) | ✅ No restrictions |
| **2** | CHKO (landscape protected areas) | ✅ Free pedestrian movement |
| **3** | National Parks, Zone C | ⚠️ Marked trails only |
| **4** | Nature reserves, Zone B | ⛔ Marked trails only, additional restrictions |
| **5** | Strict reserves, Zone A | 🚫 No disturbance — radio may be prohibited |

## Data sources

- **Summit coordinates**: [SOTA summitslist.csv](https://www.sotadata.org.uk/summitslist.csv) via GPX export
- **Protected areas**: [Štátna ochrana prírody SR](https://www.sopsr.sk/) — bounding box classification + individual web research for NP summits
- **Map overlay**: [ŠOPSR GeoServer WMS](https://maps.sopsr.sk/geoserver/ows) — official protection zones
- **Seasonal closures**: [TANAP](https://www.tanap.org/navstevny-poriadok/), [NAPANT](https://www.napant.sk/), hiking.sk

## ⚠️ Important disclaimer

**This data is AI-generated and NOT fully verified.** Every summit has a `v` (verified) field:
- `"v": 0` — AI-generated classification based on bounding box overlap and web research. **Check before activation!**
- `"v": 1` — Verified by a human operator against [maps.sopsr.sk](https://maps.sopsr.sk/)

42 summits in National Parks have been individually researched with specific notes. The remaining ~82 NP summits have base level 3 assigned but may have NPR/PR overlaps raising them to level 4–5.

**Always verify on [maps.sopsr.sk](https://maps.sopsr.sk/) before activating any summit rated level 3+.**

## Features

- 🗺️ Interactive Leaflet map with all 379 summits color-coded by protection level
- 🔍 Search by code, name, or protected area
- 🏷️ Filter by region (BA–ZA), protection level (1–5), and verification status
- 🛰️ ŠOPSR WMS overlay toggle — see official protection zones on the map
- 🌙 Dark/light theme with system preference detection
- 📋 Summit data in `summits.json` — one per line, easy to edit and contribute

## How to contribute

The best way to help is to **verify summits**:

1. Open `summits.json` in a text editor
2. Find the summit by its code (e.g. `OM/ZA-014`)
3. Check it on [maps.sopsr.sk](https://maps.sopsr.sk/) — enable the "Stupne ochrany" layer
4. Update the fields:
   - `"rl"` — researched level (e.g. `"3"`, `"4"`, `"5"`)
   - `"st"` — status: `"safe"`, `"ok"`, `"caution"`, or `"danger"`
   - `"nt"` — your notes (what you found)
   - `"v": 1` — mark as verified
5. Submit a pull request

### Data fields reference

```
c   = summit code (OM/XX-NNN)
n   = summit name
la  = latitude
lo  = longitude
e   = elevation in meters
r   = region code (BA, BB, KE, NR, PO, TN, TT, ZA)
rn  = region name
p   = SOTA points
a   = activation count
ar  = protected area name (or empty)
ac  = area category (NP, CHKO, or empty)
bl  = base protection level (1–5, from bounding box)
rl  = researched protection level (may differ from bl)
st  = activation status: safe / ok / caution / danger
nt  = notes (Slovak/English)
v   = verified: 0 = AI-generated, 1 = verified by operator
```

## Hosting on GitHub Pages

The live version is at **[trgosk.github.io/sota-om-summits](https://trgosk.github.io/sota-om-summits/)**.

To fork and host your own:
1. Fork [github.com/trgosk/sota-om-summits](https://github.com/trgosk/sota-om-summits)
2. Go to Settings → Pages → Source: `main` / `/ (root)`
3. Your map will be live at `https://your-username.github.io/sota-om-summits/`

## Tech stack

Single `index.html` + `summits.json` data file, no build step:
- [Vue.js 3](https://vuejs.org/) (CDN)
- [Leaflet](https://leafletjs.com/) (CDN)
- [CARTO basemap](https://carto.com/basemaps/) (light, inverted for dark mode)
- [ŠOPSR GeoServer WMS](https://maps.sopsr.sk/geoserver/ows) (optional overlay)
- Fonts: [Outfit](https://fonts.google.com/specimen/Outfit) + [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono)

## License

MIT — see [LICENSE](LICENSE)

Data derived from public sources (SOTA database, ŠOPSR). Summit coordinates © SOTA. Protection area data © Štátna ochrana prírody SR.

---

73 de OM operators! 🏔️📻
