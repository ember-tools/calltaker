# Calltaker

Training for the emergency call intake of the Berlin fire brigade. A trainee takes incoming calls
and interrogates them until everything a dispatch needs is known; a trainer plays the callers by
voice and watches the trainee's screen live. After every call a debrief compares what was taken
with what the scenario held.

The interface is German throughout. It runs at <https://calltaker.chojo.dev>.

## Development

Everything goes through `./toolchain.sh`, which runs inside the nix environment of `shell.nix`
(approve it once with `direnv allow`).

```bash
./toolchain.sh be-install       # backend dependencies
./toolchain.sh fe-install       # frontend dependencies
./toolchain.sh be-dev           # backend on :8000
./toolchain.sh fe-dev           # frontend on :5173, proxied to the backend
./toolchain.sh verify           # what CI runs
./toolchain.sh help             # every command
```

The same in Docker, without a local Python or node:

```bash
./toolchain.sh docker-app       # development stack on :5173 and :8000, rebuilt each time
./toolchain.sh docker-app-down  # stop it
./toolchain.sh docker-build     # the production image
```

## Map and addresses

Map tiles come from OpenStreetMap through the server's own cache (`/kacheln/…`), as the tile
usage policy asks. Address completion and the addresses of generated scenarios come from the
city of Berlin's address list ([Adressen Berlin WFS](https://gdi.berlin.de/services/wfs/adressen_berlin),
Datenlizenz Deutschland Zero 2.0), which the server downloads in the background into its data
folder; `./toolchain.sh data-adressen` loads it on purpose. Places without a house number
(parks, stations, hospitals, allotment gardens) come from
[OpenStreetMap's Berlin extract](https://download.geofabrik.de/europe/germany/berlin.html)
(© OpenStreetMap contributors, ODbL), reduced to named places in `daten/orte/` and stored with
Git LFS; `./toolchain.sh data-orte` derives them anew from today's extract. Clone with Git LFS
installed, or run `git lfs pull`, to get the file.

## Licence

GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`), see `LICENSE`.

The question graph in `daten/abfrage/` is derived from
[alarmzettel](https://github.com/rainbowdashlabs/alarmzettel). Its medical codes and reasons come
from the Berlin fire brigade's open data
([BF-Open-Data](https://github.com/Berliner-Feuerwehr/BF-Open-Data)) and remain under the fire
brigade's own terms. The fire and technical rescue protocols are invented placeholders: the real
Alarm- und Ausrückeordnung is not public.

The instructions to the caller in `daten/anleitungen/` (what to do until help arrives) are written
for training from general public guidance: the fire brigades' fire safety advice and the ERC
guidelines 2021 for first aid and basic life support. They have not been checked by a medical or
fire service authority and are shown as written.
