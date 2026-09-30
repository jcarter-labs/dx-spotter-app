# Constitution

RULE: Build from masterplan.md, idea.md and my screenshot; borrow language, tools, specs, or open-source code from examples as I choose.
RULE: At the start of the build, check tools, libraries, GitHub login, and this folder's repo on my platforms; show pass/fail.
RULE: After each change, measure the app against the Spec's screen list; show pass/fail.
RULE: After each working step: run all tests, show me proof, commit, and push to GitHub.
RULE: When code and masterplan disagree, propose only major changes, one line each; update the masterplan after I approve.
RULE: Measure UI layout with pixels against reference measurements; never claim "matches" from a visual impression.
RULE: Keep the app responsive while it works, never stuck waiting on data or input.
RULE: Keep a short list of known limitations in the masterplan; update it as we go.

# Spec

## Summary

DX Spotter ("RBN & POTA Spotter") is a macOS desktop graphical bandmap for a CW/DX operator, modelled on the N1MM bandmap (the example app). It connects to the NC7J AR-Cluster (telnet, nc7j.com:7373, login N6YU) and plots CW spots from the chosen Local or Regional Reverse Beacon skimmers on a vertical, linear frequency scale, each call sign on a leader line to its frequency. A second scale on the right shows POTA.app spots, polled every minute. The operator sets the centre frequency (HF only) and bandwidth, and spots fade out over a 5, 10 or 15 minute window. Clicking a call sign copies it to the clipboard for a logger or QRZ.com lookup. RBN spots are blue and POTA spots green. A side panel shows the controls, cluster connection status, POTA poll age and the count of spots shown. The window is resizable.

## Scope of this iteration

All seven features in `idea.md` must work this iteration. Nothing is deferred.

1. Linear-frequency bandmap of RBN spots: in
2. Local/Regional spotter toggle: in
3. Centre frequency and bandwidth controls: in
4. Click a call sign to copy it: in
5. Spot fading over time: in
6. POTA spots on the right-hand scale: in (this iteration includes both data sources, A and B)
7. Resizable window: in

## Features

Numbered as in `idea.md`, most important first. Defaults: frequency 14.045 MHz, bandwidth 50 kHz, window 10 min, spotter Regional (as in the screenshot), server NC7J.

1. **Linear-frequency bandmap of RBN spots**
   - Does: nothing needed beyond the app connecting to the cluster (`nc7j.com` port 7373, login N6YU).
   - Sees: a vertical RBN scale, linear, higher frequency at the top, spanning centre frequency ± bandwidth/2 (default 14.020 to 14.070 MHz). Each CW spot from NC7J appears as a blue call sign, call sign only, on a leader line to its frequency. Only spots from the selected spotter list are shown. Duplicates are not filtered by the app; the cluster's own deduplication is relied on.
   - Testable: a spot at frequency f inside the span is drawn at a vertical position linear in f; a spot outside the span is not drawn; a spot with a non-CW mode is not drawn; a spot from a skimmer not in the selected list is not drawn.

2. **Local / Regional spotter toggle**
   - Does: selects Local or Regional with the radio buttons.
   - Sees: only spots from that list's skimmers.
   - Local: W6YX, AK6RI-1, N6TV. Regional: K6FOD, WA7LNW, ND7K, K7CO, NG7M, N7VVX, N7TUG, KD7EFG, KW7MM, KW7MM-2.
   - Testable: exactly one radio button is selected at any time; switching changes the displayed set to spots from the matching list only; the "Shown: RBN n" count matches the spots on screen.

3. **Centre frequency and bandwidth controls**
   - Does: types a frequency in MHz and presses Set; picks a bandwidth from the menu.
   - Sees: the scale re-centres on the frequency and spans ± bandwidth/2.
   - Testable: frequency accepted from 1.8 to 30 MHz inclusive; an entry outside that range, or not a number, is rejected and the current frequency is kept; bandwidth menu offers exactly 10, 20, 40, 50, 80, 100 kHz; Window span = bandwidth (for example 50 kHz at 14.045 shows 14.020 to 14.070).

4. **Click a call sign to copy it**
   - Does: clicks a call sign on either scale.
   - Sees: nothing more is specified for feedback.
   - Testable: after the click, the clipboard contains exactly that call sign and nothing else (no frequency, no extra text).

5. **Spot fading over time**
   - Does: sets Window (min) from the menu.
   - Sees: a spot is solid when new, grows more transparent as it ages, and disappears at the Window setting.
   - Testable: Window menu offers exactly 5, 10, 15 minutes; a spot is fully opaque at age 0; its transparency increases with age; it is gone at age = Window (for example 10 min at the default, 15 min at 15); the "Shown" counts drop when a spot disappears. Clear removes all displayed spots immediately.

6. **POTA spots on the right-hand scale**
   - Does: nothing; it runs automatically.
   - Sees: a second vertical scale on the right, ticks only, with green call signs on leader lines, from the POTA.app API, call sign only. Same frequency span as the RBN scale. Fades by the same Window setting.
   - Testable: the API is polled every 60 s; the panel shows "POTA: last poll Ns ago", with N counting up since the last poll and resetting after each poll; "Shown: ... POTA n" matches the POTA spots on screen.

7. **Resizable window**
   - Does: drags the window edges.
   - Sees: the layout follows the new size.
   - Testable: the window can be resized; the control panel and status lines stay fully visible; the scales stretch to the new canvas height.

### Side panel status (from the screenshot and `idea.md`)
- Green dot and "Cluster: NC7J" when connected. Any other state is not specified.
- "POTA: last poll Ns ago".
- "Shown: RBN n · POTA n".

### Decisions on points `idea.md` left open

1. Status dot: green connected, amber connecting, red disconnected. Auto-reconnect with backoff 5, 10, 30 s, then every 60 s; show retry count.
2. Fade: linear from full opacity to 15% over the selected window (5, 10 or 15 min, default 10); never fully invisible; drop the spot when older than the window.
3. Minimum window: 400 x 700 px; layout scales above that; the screenshot (492 x 1189) is the reference.
4. Overlapping calls: at least one text height between labels; push crowded labels apart with a thin leader line to the true frequency.
5. POTA: CW only; drop spots with no frequency or outside the displayed frequency window.

## Data sources and how we'll check each one

Only two sources feed the app. Everything else on screen comes from the operator's own controls.

### Source A: NC7J AR-Cluster (RBN spots)
- Where: telnet to `nc7j.com` port 7373, login callsign N6YU.
- Used for: the left (RBN) scale. CW spots only, call sign only, from the selected Local or Regional skimmer list.
- Expected line format (to be confirmed from a live capture, not assumed): `DX de <skimmer>: <freq kHz> <call> CW ...`.
- Skimmer match: a line's skimmer matches a list entry when it equals the entry, optionally followed by a trailing `-<digits>` or `-#`. Examples: AK6RI-1 matches AK6RI-1-# and AK6RI-1-2; it does not match AK6RI-10 or AK6RI. A bare entry matches itself: W6YX matches W6YX, W6YX-# and W6YX-2. The Regional list stays as written, including KW7MM-2.
- CW check: the client-side CW check is authoritative. Server-side mode filtering is not trusted, so every line is checked for CW in the app regardless of what the server was asked to send.
- Checks:
  1. Connect: a login to the real server succeeds within 10 s and the dot goes green. Record a raw capture to a file in this folder, taken before any filtering, of 50 spot lines or 5 minutes, whichever comes first.
  1a. Server band filter: after login, the server-side band filter command is sent and the server acknowledges it. The exact command and acknowledgement text are not in `idea.md`; they stay open until a live session, then are recorded in Tech. Which band(s) the filter asks for is also not specified.
  2. Parse: replaying the capture through the parser gives, for every line, frequency (kHz to MHz), call, mode and skimmer, or an explicit reject. No line is silently lost. Count accepted plus rejected equals lines read.
  3. Filter: from the capture, only CW lines from the selected list are shown, using the skimmer match and client-side CW check above; switching Local/Regional changes the set as in Features #2. The capture must include lines that test the match: a matching suffix, a non-matching suffix, and a non-CW mode. If the 5-minute capture has none, these cases are added as hand-made test lines and marked as such.
  4. Range: spots outside the displayed window are not drawn; spots inside are placed linearly.
  5. Failure: dropping the connection turns the dot red, then amber while retrying at 5, 10, 30 s, then every 60 s, with the retry count shown; on reconnect the dot returns to green. Tested by killing the socket and by blocking the network.
  6. Bad data: a malformed or truncated line is skipped, logged, and never crashes the app.

### Source B: POTA.app API (POTA spots)
- Where: the POTA.app spots API. The endpoint is not given in `idea.md` and is chosen in Tech.
- Used for: the right (POTA) scale. CW only, call sign only, polled every 60 s.
- Checks:
  1. Poll: a live request succeeds and returns spots. Record one raw response to a file in this folder.
  2. Parse: replaying the recording gives frequency, call and mode for each spot, or an explicit reject. Accepted plus rejected equals spots returned.
  3. Filter: non-CW spots, spots with no frequency, and spots outside the displayed window are dropped (decision 5).
  4. Timing: requests are 60 s apart, within 2 s; "POTA: last poll Ns ago" counts up and resets after each poll.
  5. Failure: a timeout, an HTTP error, or bad JSON leaves the existing POTA spots in place, does not crash the app, and the next poll after 60 s tries again. The "last poll" age keeps counting from the last success.
  6. Counts: "Shown: POTA n" equals the POTA spots on screen.

### Checks that need no network
Parser and filter checks run on the saved captures, so tests run offline and give the same result each time. The live connect and poll checks are run separately and their results shown as pass/fail.

### Status display
The status dot covers the cluster only. POTA shows its poll age ("POTA: last poll Ns ago"); a POTA failure does not change the dot.

### Open points
- The POTA.app endpoint and its JSON fields stay open for Tech.
- The server-side band filter command, its acknowledgement text, and which band(s) it requests (see check 1a).

## Screen list

Source: `screenshot.png` (492 x 1189 px, Linux window; macOS native chrome replaces the title bar). Positions are x, y in screenshot pixels, read by eye, not measured, and approximate.

Window
1. Title bar: "DX Spotter", centred at the top; window buttons at the top right (y ~20). Replaced by macOS chrome.
2. Heading: "RBN & POTA Spotter", bold, large, centred across the full width (y ~68).
3. Horizontal rule under the heading, full width (y ~93).

Left area: bandmap canvas, white background, x 0 to ~298, y ~127 to the bottom
4. Column label "RBN" above the left scale (x ~72, y ~115), bold.
5. Column label "POTA" above the right scale (x ~222, y ~115), bold.
6. RBN scale: vertical line at x ~105. Tick labels to its left at 14.070 (top, y ~149), 14.060 (y ~352), 14.050 (y ~555), 14.040 (y ~760), 14.030 (y ~963), 14.020 (bottom, y ~1168). Small ticks at each label. Higher frequency at the top.
7. RBN spots: call signs to the right of the RBN line, left-aligned at x ~113, each joined to its frequency on the line by a short leader line. Names are spread apart vertically where frequencies are close. Fading shown as lighter text; older spots are paler.
8. POTA scale: vertical line at x ~284 with ticks only, no labels.
9. POTA spots: call signs to the left of the POTA line, right-aligned (ending x ~273), each joined by a leader line to its frequency on the line. Same fading.

Right area: control panel, light grey background, x ~298 to 492, left-aligned at x ~312
10. "Frequency (MHz)" label (y ~123).
11. Frequency text box (x 312 to ~388, y ~148) showing 14.045, with a "Set" button beside it (x ~397 to 477).
12. "Bandwidth (kHz)" label (y ~184), with a dropdown menu below it showing 50 (x 312 to ~376, y ~208).
13. "Window (min)" label (y ~245), with a dropdown menu below it showing 10 (x 312 to ~376, y ~269).
14. "Spotter" label (y ~305), with two radio buttons stacked below: "Local" (y ~326, unselected) and "Regional" (y ~349, selected).
15. "Server" label (y ~380), with a dropdown below it showing "NC7J (AR-Cluster)" (x 312 to ~466, y ~402).
16. "Clear" button, full panel width (x 312 to ~477, y ~443).
17. Status line: green dot and "Cluster: NC7J" (y ~485).
18. Status line: "POTA: last poll 57s ago" (y ~507).
19. Status line: "Shown: RBN 43 · POTA 26" (y ~527).

# Tech

## Language and tools (chosen by the operator)

| Area | Choice | Why |
|---|---|---|
| Language | Python, in a venv at `./.venv` | Matches the operator's other projects and global setup. |
| GUI | Tkinter (ttk widgets, Canvas for the bandmap) | The screenshot looks like a Tk app; Tk ships with Python; Canvas suits scales, leader lines and click-to-copy. Fading is done by blending the text colour toward the white background, since Tk has no text transparency. |
| Cluster link | Standard-library `socket` in a worker thread, spots passed to the GUI through a queue | No extra package; fits Tk's event loop. `telnetlib` is not used (removed in Python 3.13). |
| POTA HTTP | `requests`, polled every 60 s in a worker thread | Simple timeouts and error handling for the failure checks. |
| Screenshot measuring | Pillow | Reads `screenshot.png` pixels for Task 1 and for layout checks. |
| Tests | pytest | Offline parser and filter tests on the saved captures; clear pass/fail. |

## Modules (proposed)

Each module has one job and can be tested on its own. Only `ui` imports Tk; every other module runs without a window.

Rules between modules:
- `layout` is pure: numbers in, numbers out, no Tk imports.
- The network clients (`cluster_client`, `pota_client`) never call the parsers. They put raw lines and raw records on a queue.
- That queue is the only link between the network side and the GUI side. Nothing else is shared between threads.
- On a failure (connection lost, timeout, HTTP error, bad data) a client puts a status item on the queue, never spots. Status items carry the state for the status dot and retry count; a POTA failure status does not reset the poll age.
- `ui` has one loop: a Tk `after()` tick that calls `app.drain()` and then redraws. There is no other loop or polling in the GUI.

1. `cluster_parse`: turns one raw cluster line into a spot (frequency, call, mode, skimmer) or an explicit reject. Tested on the saved cluster capture.
2. `pota_parse`: turns one raw POTA record into a spot (frequency, call, mode) or an explicit reject. Tested on the saved POTA response.
3. `spot_filter`: decides if a spot is shown (skimmer match, client-side CW check, frequency inside the window, POTA drops). Tested with the match and CW cases from Data sources.
4. `spot_store`: holds spots with their age, gives each one's opacity (linear to 15%), drops spots older than the window, counts per source, and clears. Tested with a fake clock.
5. `settings`: holds and validates frequency (1.8 to 30 MHz), bandwidth (10, 20, 40, 50, 80, 100), window (5, 10, 15) and the Local/Regional choice; a bad entry is rejected and the old value kept. Tested with valid and invalid inputs.
6. `layout`: maps frequency to vertical position on the scale and spreads crowded labels apart (at least one text height), keeping each leader line's true frequency. Pure, no Tk. Tested with numbers only.
7. `cluster_client`: socket worker thread that logs in, sends the band filter, puts raw lines on the queue, and reconnects with backoff; connection state and retry count go on the queue as status items. Tested against a fake local server.
8. `pota_client`: worker thread that polls every 60 s and puts raw records on the queue; on failure it puts a status item and no spots, so old spots stay. The poll age keeps growing from the last success and does not reset on failure. Tested with a faked HTTP layer.
9. `app` (approved): `app.drain()` empties the queue, calls the parsers, filter and store, applies status items (dot, retry count, poll age), and gives `ui` what to draw. No Tk and no sockets. Tested by feeding it queued items and checking the store and status.
10. `ui`: Tkinter window, canvas and side panel; its `after()` tick calls `app.drain()` then redraws, and nothing else; it only draws and sends user input on, never waits on data. Tested by measuring its screenshot against the saved measurements.

The Task 1 measuring script is a separate tool, not part of the app.

## Open until a live session

Each item below stays open until it is taken from a saved live capture, never from memory, and the capture file is named next to the item when it is closed.

| Open item | Closed by |
|---|---|
| POTA.app endpoint and JSON fields | Saved response from a live request |
| Server-side band filter command and its acknowledgement | Saved live cluster session |
| Login prompt text | Saved live cluster session |
| Real spot-line format | Saved live cluster session (raw capture, before filtering) |

# Tasks

Every step below follows the Constitution: after each working step, run all tests, show proof, commit and push; after each change to the app, measure it against the Spec's screen list. A step is not done until its "done when" line is shown as pass.

## Setup
1. Start-of-build check: Python, Tk, venv, pip, git identity, GitHub login and SSH (`ssh -T git@github.com`), and this folder's repo; show pass/fail for each. Note: this folder currently sits inside the `~/Projects` repo (git reports that as its top level), so decide with the operator whether it gets its own repo. Done when: every line passes.
2. Create `./.venv`, install requirements (`requests`, `Pillow`, `pytest`), write the environment steps to `docs/setup.md`, add `.gitignore`. Done when: `pytest` runs, with one trivial test, inside the venv.
3. Early step: measure `screenshot.png` with a script and save the measurements to a file in this folder. All layout checks against the Spec's screen list use these measurements, not the approximate positions in the Spec. Done when: the file lists a measured position and size for each of the 19 screen-list elements.

## Live captures (close the "Open until a live session" table in Tech)
4. Capture a live NC7J session: login prompt text, band filter command and its acknowledgement, and a raw capture of 50 lines or 5 minutes, saved to a file. Done when: each item is recorded in Tech with its capture file named.
5. Capture one live POTA.app response, saved to a file. Done when: the endpoint and JSON fields are recorded in Tech with the file named.

## Parsers, rules and logic (no window, no network; offline tests)
6. `cluster_parse` with tests on the saved capture. Done when: accepted plus rejected equals lines read.
7. `pota_parse` with tests on the saved response. Done when: accepted plus rejected equals records returned.
8. `spot_filter` with tests (skimmer match, CW check, frequency range, POTA drops). Done when: the matching, non-matching and non-CW cases pass.
9. `settings` with tests for valid and invalid entries. Done when: out-of-range and non-numeric frequencies are rejected and the old value kept.
10. `spot_store` with tests on a fake clock. Done when: opacity is linear to 15%, spots drop past the window, counts and Clear are right.
11. `layout` with tests (frequency to position, label spreading of at least one text height, no Tk import). Done when: tests pass, including a crowded-labels case; add any shortfall to the known limitations list.

## Network and wiring
12. `cluster_client` against a fake local server: login, band filter, raw lines on the queue, reconnect at 5, 10, 30 s then 60 s, status items. Done when: the failure check (killed socket, blocked network) passes.
13. `pota_client` with a faked HTTP layer: 60 s poll, raw records on the queue, a status item on failure with old spots kept. Done when: timeout, HTTP error and bad JSON cases pass and the poll age keeps growing on failure.
14. `app`: `app.drain()` calls the parsers, filter and store and applies status items. Done when: queued items give the right store contents, counts and status.

## Window
15. `ui` static layout with fake spots, built from the step 3 measurements. Done when: the measured layout is compared with the screenshot measurements and shown as pass/fail per screen-list element.
16. Wire the controls to `settings` (Set, Bandwidth, Window, Spotter, Server, Clear), with the `after()` tick calling `app.drain()` then redraw. Done when: each control works and the window stays responsive.
17. Connect live RBN spots to the left scale: blue call signs, leader lines, click to copy, cluster status dot and retry count. Done when: a live session shows spots and the clipboard holds exactly the clicked call sign.
18. Connect live POTA spots to the right scale: green call signs, ticks only, "last poll Ns ago". Done when: a live poll shows spots and the counts match what is on screen.
19. Fading and resizing: fade to 15% and drop at the window age; minimum size 400 x 700, layout scales above it. Done when: the fade values and the size checks pass by measurement.

## Finish
20. Full check: the screen-list measurement, both source checks live, failure tests, and a responsiveness check. Update the known limitations list. Done when: every check shows pass, and any fail is fixed or listed.
21. Working app: one documented launch command, `docs/setup.md` complete, final test run, commit and push. Done when: the app starts from a fresh clone following only `docs/setup.md`.
