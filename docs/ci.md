# Continuous integration

The CI workflow runs on pull requests and pushes to `main`. Its manual Run workflow
entry checks every registered environment. It makes no subscription or paid API calls.

Shared tests run on every change. Environment checks use the PR's complete diff
from its merge base, or the before/after commits for a push. Renames include both
paths. The job summary lists selected environments and the paths that selected them.

| Changed files | Environment checks |
| --- | --- |
| Environment source, registered runner, task tests, policies, recipes, profiles or assets | That environment |
| Requirements, including recursive `-r` references, or installation metadata | Every environment that consumes the file |
| Shared runtime, registry, root dependency configuration or CI code | Every registered environment |
| Markdown documentation only | Shared tests |
| Other unclassified files | Every registered environment |

Selection also follows current cross-game consumers: Asterix and Badminton use
Touhou's API/budget code, and TableTennis uses Badminton's public-observation code.
Changes select those consumers transitively. Update these small ownership rules
when moving or removing the shared code.

The matrix reads environment names, Python versions and installation entries from
`environments/registry.json`. Every selected environment starts with an empty project
cache, runs `sol env setup GAME`, checks dependencies with `uv pip check`, and runs
its existing offline suites in its own interpreter. Only package download/build
caches persist between jobs. Test suites use separate processes to isolate their
module search paths.

The root `ci` dependency group belongs to shared tests. Its pinned `imageio-ffmpeg`
wheel supplies the FFmpeg executable for media tests through a temporary PATH entry.
This keeps media validation independent of system FFmpeg installation and apt
downloads. The shared job also checks the CLI without loading third-party packages.
Missing uv, empty suites and unexpected skips fail the job.

Environment jobs use Ubuntu's official HTTPS package mirror. System dependency
steps have a five-minute timeout so a stalled download fails promptly. Native
compilation retains the environment job's separate 60-minute limit.

Touhou tests use a frontend bound to `127.0.0.1` on an available port. Rhythm tests
load its real page, capture pixels, execute a literal key, and close the browser
under virtual and native clocks. Asterix replays saved actions; this remains replay
evidence. Tetris runs engine, executor, rules-baseline and zero-model replay contracts without model calls. PCBA runs its CPU tests and registered no-model smoke command. CI does not
apply strict wall-clock performance thresholds to shared runners.

Racing, Badminton and TableTennis installation and CPU contracts run automatically.
TableTennis flight and servo checks use the prepared native source.
GPU-dependent Badminton and TableTennis tests report their explicit skip reasons
in the job summary. PvZ and VERA20K setup compiles and imports the native extension.
Their resource-dependent gameplay is outside automated coverage. Passing CI does
not certify those omitted GPU/gameplay checks or model performance.

Configure the repository's branch protection or ruleset to require the fixed `ci`
check. That job always runs and rejects failed or cancelled prerequisites and
unexpectedly skipped environment jobs. A documentation-only selection permits the
environment matrix to skip while still requiring shared tests.

RoboOlympics is private. Configure the Actions secret `CI_SOURCE_READ_TOKEN` with
read-only Contents access to `CHIGUI0/roboolympics`. The default workflow token only
covers this repository. The CI installer supplies the source token through Git's
process environment and removes it before running tests. Credentials are not
written to source files, Git remotes or cached virtual environments. Without this
secret, private-source installation fails rather than skipping its checks.

Run the same checks locally after installing the documented host libraries:

```bash
uv sync --locked --group ci --python 3.12
uv run --no-sync python scripts/ci.py shared
uv run --no-sync python scripts/ci.py select --base origin/main
uv run --no-sync python scripts/ci.py select --all
XDG_CACHE_HOME=/tmp/sooool-ci-local uv run --no-sync python scripts/ci.py environment rhythm
```

An environment check prepares the selected game through the normal installer.
Use a separate `XDG_CACHE_HOME` for a clean installation check. GPU/native tests
remain available through their existing suites on hosts with the required sources,
resources and graphics support.
