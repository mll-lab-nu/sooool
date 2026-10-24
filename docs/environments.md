# Prepare game environments

[CI coverage and local checks](ci.md) use the same registered installation entrypoint.

Install [uv](https://docs.astral.sh/uv/) and Git, then bootstrap the project:

```bash
uv sync --locked --python 3.12
uv run sol env list
uv run sol env setup tabletennis
export MUJOCO_EGL_DEVICE_ID=0  # use an allocated GPU
uv run sol simulate tabletennis --output runs/tabletennis-001
```

`setup` installs one game into its own Python virtual environment.
Local games use this checkout. External games fetch the registered commit.
It reuses prepared sources and virtual environments. Launch commands select
the matching Python and source directory without shell activation.
They preserve the caller's working directory and relative output paths.
An unprepared or outdated environment reports the required setup command.

External sources, all game venvs and preparation records live in `~/.cache/sooool/`.
`XDG_CACHE_HOME` selects another cache location. Racing, Badminton and
TableTennis share the pinned RoboOlympics source but have separate venvs.
Asterix, Tetris, Touhou, Rhythm and PCBA use this checkout and separate cached venvs.
PCBA retains Python 3.11. The three original games use Python 3.12.
The root `.venv` contains only the `sol` launcher. Install only the games you need:

```bash
uv run sol env setup asterix
uv run sol env setup tetris
uv run sol env setup touhou
uv run sol env setup rhythm
uv run sol env setup pcba
```

Touhou and Rhythm setup installs their Gym packages and Chromium. Asterix does
not install browser dependencies. System graphics drivers, Node.js for Touhou's
Gym bridge, and browser system libraries remain host prerequisites. On Linux,
install missing Chromium system libraries with
`uvx --from playwright==1.58.0 playwright install-deps chromium`.

A setup installs dependencies once per game and reuses download caches. Subsequent
launches reuse that game's venv. Setup records the checkout path and installation
inputs. Re-run setup when switching checkouts or changing dependency declarations.
Local source edits are used directly. `--source` applies only to external games.

Prepare several games with `uv run sol env setup asterix touhou rhythm`, or
prepare every registered game with `uv run sol env setup all`.
`bash scripts/setup.sh asterix touhou` also bootstraps the root launcher and
submodule before preparing the selected games. The script requires a selection.
`--source` accepts exactly one external game.

Setup stops if installation or compilation fails. Native setup also imports the
compiled PvZ or VERA20K extension before marking the environment ready. Setup does
not open a game or make model calls. The `ready` status records prepared sources and Python/browser packages.
Install host libraries before running a browser game. Resource loading and graphics
errors surface when the game runs. PvZ and VERA20K setup verifies compiled imports;
their native gameplay tests require separate game resources and graphics support.

`sol env list` reports each game's preparation status and supported commands.

The registry declares each runner's supported commands. All registered commands
use the same launcher, including PCBA simulation, reports and video export.
Unsupported commands fail explicitly. Existing replay and Asterix video scripts
also select the prepared game interpreter when launched through the root Python.

Use an existing checkout for development:

```bash
uv run sol env setup vera20k --source /absolute/path/to/vera20k-agent
```

This records the checkout without switching or resetting it. Later launches use
that source until the next setup. Setup without `--source` selects the registered
commit. Managed source edits stop setup instead of being overwritten.

Setup compiles these environments and installs their Python 3.12 packages:

| Environment | Prepare | Build requirements and guide |
| --- | --- | --- |
| Red Alert 2: Yuri's Revenge (VERA20K) | `uv run sol env setup vera20k` | Rust, Maturin, and Linux native libraries. [Python API and installation guide](https://github.com/mindorigin150/vera20k-agent/blob/c9a9b38f2e42042f398a39a4f07edcd0feba0219/python/README.md). |
| Plants vs. Zombies (PvZ) | `uv run sol env setup pvz` | CMake, Ninja, and Linux native libraries. [Installation and native validation guide](pvz.md). |

The VERA20K revision includes the offscreen HUD update fix. Re-run
`uv run sol env setup vera20k` to rebuild an existing environment.

Both environments keep game resources outside this repository.
Their model experiment runners are later integrations. Setup prepares their native
APIs. Re-run setup after native source changes.

`environments/registry.json` owns source revisions, Python versions, install
steps and existing runner commands. Recipes own experiment conditions, and
policies own gameplay decisions. Add a registry entry and the game's own runner
when introducing an environment.

## Shared experiment options

Use `--provider subscription|api|rules` to explicitly select an existing decision
source. Each game preserves its own default and supports only its existing
providers. The command help lists the accepted values. `simulate` uses the existing
subscription simulation path, with explicit rules simulations retained where the
game already supports them. Subscription simulations never fall back to an API.

`--duration` is game time in seconds. `--wall-seconds` limits wall time where
supported, including PCBA eval/pipeline and process-clock preflight. Touhou runs a complete game, and Rhythm durations must match the chart.
`--output`, `--seed` and `--max-calls` retain each game's existing limits and defaults.

Paid commands read `OPENAI_API_KEY` from process memory or prompt without echo at
an interactive terminal. `--ledger` selects a cumulative budget ledger.
`--budget-usd` declares its total ceiling, and `--stage-cap-usd` retains an existing
stage ceiling where supported. Racing creates its ledger with `sol budget racing`;
its paid runs require that existing ledger and an explicit stage cap. Existing
ledger formats, charges, reservations and settlement rules remain game-owned.

New experiment runs share `evaluation-record.json`. Register one with
`sol record RUN`; the default registry is `artifacts/GAME/evaluations.jsonl`.
Add `--decision retain|reject|diagnostic --note TEXT` to append a research judgment.
See [evaluation records](evaluation-records.md) for the shared record contract.
