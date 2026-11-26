# Guild Tabard Designer

Design a World of Warcraft guild tabard with exactly the options of the in-game guild tabard vendor, then see it worn
in 3D on the game's own character models.

Live: https://tabard.happyfanclub.fun

- 196 emblems in 17 colours, 6 borders in 17 colours, 51 background colours: the vendor's options, nothing added and
  nothing left out. They come from the game's own tables and are the same in WoW Forever, Retail, Mists of
  Pandaria Classic, Anniversary and Classic Era.
- **Crest** view: Blizzard's Armory tabard art, tinted to the measured in-game cloth colours.
- **Character** view: the playable races of WoW Forever (the eight original races and the Skyborne), male and
  female, in the first frame of their Stand animation, wearing the in-game Guild Tabard textures. Optional Tier 0.5 set
  (Dungeon Set 2: helmet, shoulders, gloves, bracers, legs, boots, chest under the tabard) and Tier 1 belt
  over the waist; with the belt hidden the tabard cloth runs on over it. A Chest slider (for fun) swells the chest,
  which sways on a spring when the character turns.
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
python fetchmodels.py     # resolve and download the 18 character models and their textures
python export.py check    # optional: renders a check sheet of all models to the cache folder
python export.py export   # docs/models: posed meshes, skins, hair
python build_belts.py     # docs/models/belts: Tier 1 belt textures
python build_sets.py      # docs/models/sets + items: Tier 0.5 sets (textures, geosets, helmets, shoulders)
```

Eye textures come from the first Eye Color choice (Eye Glow for the Undead) in the ChrCustomization tables.
`tools/overrides.json` holds the fixes the data cannot tell: extra geosets (Undead bones and jaw, Tauren horns, Skyborne
eyebrows), a brown Tauren fur, and the Skyborne file IDs. Those files have no listfile name; they come from ChrModel
218/219 and the first Skin Color, Face, Hair Style and Hair Color choice in the ChrCustomization tables of WoW Forever
(build 1.60.1.71091).

## Sources

- Game tables and files: [wago.tools](https://wago.tools) (DB2 exports and CASC file downloads).
- Crest art: Blizzard's Armory tabard renderer (`render.worldofwarcraft.com/us/guild/tabards/`).
- 3D: [three.js](https://threejs.org) r128 from cdnjs.

## Notice

A free, non-commercial fan project, not made or endorsed by Blizzard Entertainment. World of Warcraft and its art,
models and textures are trademarks and copyright of Blizzard Entertainment, Inc., used under Blizzard's fan content
policy.
