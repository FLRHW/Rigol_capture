# Rigol Capture — Session State

Last reviewed: 2026-11-15
Repository: `FLRHW/Rigol_capture`
Default branch: `main`

## Branch / commit status
- This initial documentation is being committed directly to `main`.
- The first documentation commit created `docs/PROJECT_HANDOVER.md`: `7b18f1206f215ab5c903c9b2863f5a1eaa48b557`.
- The commit that adds **this** file will be the current branch HEAD. Obtain its exact SHA with `git rev-parse HEAD` after fetching or via GitHub's commit history. Do not treat the SHA above as the final HEAD.
- At documentation initialisation, the repository did not contain application source.

## Existing local source, not yet on GitHub
Developer-reported local folder:
`/mnt/Data/01_Engineering/01_Projects/301_Rigol_DS1054Z/Rigol_capture`

Files reported (contents not yet reviewed):
- `README.txt`
- `README_v2_1.txt`
- `rigol_ds1054z_capture.py`
- `test_rigol_capture.py`
- `test_rigol_decimation.py`

**Important:** This folder has not been inspected through the GitHub connector. Before importing it, inspect its Git status and existing remotes; preserve local changes and do not overwrite any file.

## Implemented in committed application source
None verified. The initial GitHub repository contained no committed application source.

## Offline-tested
None verified against committed application source. Local test scripts exist by filename only; their results are unknown.

## Hardware-validated
None verified against committed application source. Past DS1054Z observations are not evidence of a successful capture tool test.

## Test evidence
- GitHub repository inspection: initially empty, default branch configured as `main`.
- Docs created via GitHub connector.
- No Python tests or physical captures executed as part of this documentation initialisation.

## Known issues / uncertainties
- Actual Python implementation, dependencies, capture architecture, CLI, and tests still need source review.
- Local Git state unknown; first sync must avoid clobbering local files.
- Rigol DS1054Z CH3 DC-drift anomaly remains unresolved, independent of tool validation.
- Instrument network connectivity from the application remains unverified.

## Next steps
1. Inspect local directory: `git status`, `git remote -v`, `git branch -avv`, and `git log -1 --oneline` (if Git exists).
2. If local directory has no `.git`, initialise Git, fetch `origin/main`, and establish tracking *without overwriting* the five local files. If it already has Git history, reconcile history safely before pulling.
3. Review and commit local application sources and READMEs (excluding local secrets, large captures or generated data); push to `main`.
4. Review both README versions and Python code; update architecture and actual implemented features accordingly.
5. Run offline tests; record exact command/results and revision.
6. Test captures on the physical DS1054Z; record instrument settings, transport, output and outcomes.
7. Update both documents after substantive changes, and ensure the recorded state reflects committed files before ending sessions.
