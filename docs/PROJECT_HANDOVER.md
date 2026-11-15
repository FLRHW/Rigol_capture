# Rigol Capture — Project Handover

Last reviewed: 2026-11-15

## Purpose and scope
Develop a Python capture tool for the Rigol DS1054Z oscilloscope, intended to retrieve waveform data for analysis and export. Actual implemented behaviour must be verified from source after the first source upload.

## Local project context (not yet committed)
The developer reports the following files in the local working directory:
- `README.txt`
- `README_v2_1.txt`
- `rigol_ds1054z_capture.py`
- `test_rigol_capture.py`
- `test_rigol_decimation.py`

Local directory: `/mnt/Data/01_Engineering/01_Projects/301_Rigol_DS1054Z/Rigol_capture`.
These filenames indicate a working codebase and tests, but their contents and execution results are **not verified**. Do not infer supported functionality from their names.

## Record-keeping policy
- The committed repository is the authority for implemented features; uncommitted local work must be identified separately.
- Maintain this file for architecture, requirements, engineering decisions, safety constraints, and durable historical findings.
- Maintain `docs/SESSION_STATE.md` for current branch/commit, implementation, test evidence, known issues, and next actions.
- Update both after significant changes and hardware tests. Before ending a session, compare the documents with the actual committed code.
- Never treat ChatGPT history as the only record of important project knowledge.

## Status definitions
- **Implemented:** present in committed source (not necessarily tested).
- **Offline-tested:** verified without the actual instrument, with evidence and revision recorded.
- **Hardware-validated:** exercised on a real oscilloscope, with test conditions, observed results and revision recorded.
- **Planned:** not implemented in committed application source.

## Architecture and requirements
Pending review of the existing local Python scripts and READMEs after they are committed. Record instrument transport, SCPI commands, capture modes, data scaling and raw formats, metadata, exports, CLI/GUI behaviour, dependencies, failure/retry handling, and test procedures as verified.

## Historical instrument observations (not capture-tool validation)
- Instrument: Rigol DS1054Z.
- Separate Ethernet work used a link-local `169.254.x.x` arrangement; application communication has not been confirmed.
- CH3 previously exhibited slow or drifting DC readings near a 25 V stimulus, while CH2 read correctly. The cause remains unresolved. Keep hardware anomaly investigation distinct from capture-tool software testing.

## Engineering and safety constraints
- Confirm probe attenuation, permitted input voltages, grounding and test setup using manufacturer guidance before attaching signals.
- Retain acquisition parameters and waveform scaling metadata; never silently label incomplete or invalid transfers as valid.
- Report transport/SCPI errors and disconnections explicitly.
- These are **design constraints**, not claims of implemented safeguards.

## Significant-change checklist
1. Reconcile this document with actual source and significant design decisions.
2. Record exact branch and HEAD SHA, tests, equipment setup and remaining issues in `SESSION_STATE.md`.
3. Separate implemented, offline-tested, hardware-validated, and planned work.
4. Document reproducible tests, especially instrument observations.
5. Confirm documentation matches committed code before calling a session complete.
