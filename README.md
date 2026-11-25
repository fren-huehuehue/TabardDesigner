# Guild Tabard Designer

Design a World of Warcraft guild tabard with exactly the options of the in-game guild tabard vendor, then see it worn
in 3D on the game's own character models.

Live: https://tabard.happyfanclub.fun

- 196 emblems in 17 colours, 6 borders in 17 colours, 51 background colours: the vendor's options, nothing added and
  nothing left out. They come from the game's own tables and are the same in Retail, Mists of Pandaria Classic,
  Anniversary and Classic Era.
- **Crest** view: Blizzard's Armory tabard art, tinted to the measured in-game cloth colours.
- **Worn in game** view: 10 races, male and female, in the first frame of their Stand animation, wearing the in-game
  Guild Tabard textures. Optional Tier 1 belt over the waist.
- Design codes and links (`#t-129-17-4-17-33`), saved designs (in the browser), copyable colour values (in-game cloth
  and the guild crest API value).

## Layout

| Folder | What |
|---|---|
| `docs/` | The static site. GitHub Pages serves this folder as is. |
| `tools/` | Python pipeline that builds the assets in `docs/` from game data. |

Binary model data and colour tables ship as base64 text (`*.b64.txt`) so the same files also work where only text
and media types are served.

## Rebuilding the assets

Needs Python 3, `curl`, and `pip install -r tools/requirements.txt`. Downloads go to a cache outside the repo
(`TABARD_CACHE`, default `~/.cache/tabard-designer`; several hundred MB, keep it off Google Drive).

```
cd tools
python build_crest.py     # docs/img: Armory art + the colour palette in index.html
python build_ingame.py    # docs/img3d: in-game emblem atlas, border/background sheets, colour tables, EMB in index.html
python fetchmodels.py     # resolve and download the 20 character models and their textures
python export.py check    # optional: renders a check sheet of all models to the cache folder
python export.py export   # docs/models: posed meshes, skins, hair
python build_belts.py     # docs/models/belts: Tier 1 belt textures
```

`tools/overrides.json` holds the fixes the data cannot tell: extra geosets (Undead bones, Tauren horns), a brown
Tauren fur, and two models pinned to build 12.1.5.70961 because the latest model file did not match its skin file.

## Sources

- Game tables and files: [wago.tools](https://wago.tools) (DB2 exports and CASC file downloads).
- Crest art: Blizzard's Armory tabard renderer (`render.worldofwarcraft.com/us/guild/tabards/`).
- 3D: [three.js](https://threejs.org) r128 from cdnjs.

## Notice

A free, non-commercial fan project, not made or endorsed by Blizzard Entertainment. World of Warcraft and its art,
models and textures are trademarks and copyright of Blizzard Entertainment, Inc., used under Blizzard's fan content
policy.
