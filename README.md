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

## Licence

GNU Affero General Public License, version 3 or later (`AGPL-3.0-or-later`), see `LICENSE`.
