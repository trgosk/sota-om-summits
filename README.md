<p align="center">
  <a href="https://trgosk.github.io/sota-om-summits/">
    <img src="icon.svg" alt="SOTA OM Summits" width="120">
  </a>
</p>

# sota-om-summits

Nature protection level database for all **379 Slovak (OM) SOTA summits**, helping ham radio operators determine which summits are safe to activate under Slovak nature protection law.

🌐 **[Live demo →](https://trgosk.github.io/sota-om-summits/)**

![screenshot](screenshot.png)

## Why?

Slovakia has 5 levels of nature protection (*stupne ochrany*). Operating a radio station in level 5 areas may be considered disturbing peace and quiet — which is explicitly prohibited. Many SOTA summits fall inside National Parks (level 3), nature reserves (level 4–5), or have specific trail closures.

This tool maps every OM summit to its protection level so you can plan activations responsibly.

## Summit categories

| Category | Meaning | SOTA impact |
|----------|---------|-------------|
| **Safe** | No restrictions | ✅ Freely activate |
| **Rules** | Conditions apply (trail, season, other) | ⚠️ Follow the rules and you're fine |
| **Stop** | Permission required from state/owner | 🚫 Do not activate without permission |

Summits also carry a protection level (1–5) from Slovak law for reference:

| Level | Territory | Note |
|-------|-----------|------|
| **1** | General (whole Slovakia) | No restrictions |
| **2** | CHKO (landscape protected areas) | Free pedestrian movement |
| **3** | National Parks, Zone C | Marked trails only |
| **4** | Nature reserves, Zone B | Marked trails + restrictions |
| **5** | Strict reserves, Zone A | No disturbance — radio may be prohibited |

## Data sources

- **Summit coordinates**: [SOTA summitslist.csv](https://www.sotadata.org.uk/summitslist.csv) via GPX export
- **Protected areas**: [Štátna ochrana prírody SR](https://www.sopsr.sk/) — bounding box classification + individual web research for NP summits
- **Map overlay**: [ŠOPSR GeoServer WMS](https://maps.sopsr.sk/geoserver/ows) — official protection zones
- **Seasonal closures**: [TANAP](https://www.tanap.org/navstevny-poriadok/), [NAPANT](https://www.napant.sk/), hiking.sk

## ⚠️ Important disclaimer

All 379 summits have been verified by operators against [maps.sopsr.sk](https://maps.sopsr.sk/). However, protection zones and trail closures can change — **always check current conditions before activating any summit categorized as Rules or Stop.**

## Features

- 🗺️ Interactive Leaflet map with all 379 summits color-coded by category (safe/rules/stop)
- 🔍 Search by code, name, or protected area
- 🏷️ Filter by region (BA–ZA) and category
- 🛰️ ŠOPSR WMS overlay toggle — see official protection zones on the map
- 🗂️ NP/CHKO boundary and nature reserve polygon overlays
- 🌙 Dark/light theme with system preference detection
- 📱 Installable PWA — add to home screen on Android/iOS
- 📶 Offline support — cached summit data and map tiles work without internet
- 📋 Summit data in `summits.json` — one per line, easy to edit and contribute

## How to contribute

The best way to help is to **verify summits**:

1. Open `summits.json` in a text editor
2. Find the summit by its code (e.g. `OM/ZA-014`)
3. Check it on [maps.sopsr.sk](https://maps.sopsr.sk/) — enable the "Stupne ochrany" layer
4. Update the fields:
   - `"cat"` — category: `"safe"`, `"rules"`, or `"stop"`
   - `"rl"` — researched protection level (e.g. `"3"`, `"4"`, `"5"`)
   - `"nt"` — your notes (what you found)
5. Submit a pull request

### Data fields reference

```
c    = summit code (OM/XX-NNN)
n    = summit name
la   = latitude
lo   = longitude
e    = elevation in meters
r    = region code (BA, BB, KE, NR, PO, TN, TT, ZA)
p    = SOTA points
a    = activation count
ar   = protected area name (or empty)
ac   = area category (NP, CHKO, or empty)
rl   = researched protection level (string, may be range e.g. "4-5")
cat  = category: safe / rules / stop
nt   = notes (Slovak/English)
v    = verified: 1 = verified by operator
```

**Rules-specific fields** (when `cat = "rules"`):
```
rules          = array of rule types: "trail", "season", "warning_other"
warning_other  = free-text warning (when "warning_other" in rules)
```

**Stop-specific fields** (when `cat = "stop"`):
```
stop           = key into stop_reasons lookup (e.g. "OSOBITA")
stop_reasons   = root-level lookup object with full stop reason text
```

## Hosting on GitHub Pages

The live version is at **[trgosk.github.io/sota-om-summits](https://trgosk.github.io/sota-om-summits/)**.

To fork and host your own:
1. Fork [github.com/trgosk/sota-om-summits](https://github.com/trgosk/sota-om-summits)
2. Go to Settings → Pages → Source: `main` / `/ (root)`
3. Your map will be live at `https://your-username.github.io/sota-om-summits/`

## Tech stack

Single `index.html` + `summits.json` data file, no build step:
- [Vue.js 3](https://vuejs.org/) (CDN, pinned to 3.5.13)
- [Leaflet](https://leafletjs.com/) (CDN)
- [CARTO basemap](https://carto.com/basemaps/) (light, inverted for dark mode)
- [ŠOPSR GeoServer WMS](https://maps.sopsr.sk/geoserver/ows) (optional overlay)
- Service worker with offline caching (app shell + Google Fonts + map tiles)
- Fonts: [Outfit](https://fonts.google.com/specimen/Outfit) + [IBM Plex Mono](https://fonts.google.com/specimen/IBM+Plex+Mono)

## License

MIT — see [LICENSE](LICENSE)

Data derived from public sources (SOTA database, ŠOPSR). Summit coordinates © SOTA. Protection area data © Štátna ochrana prírody SR.

---

73 de OM operators! 🏔️📻
