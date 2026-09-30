# Constitution

RULE: Build from masterplan.md, idea.md and my screenshot; borrow language, tools, specs, or open-source code from examples as I choose.
RULE: At the start of the build, check tools, libraries, GitHub login, and this folder's repo on my platforms; show pass/fail.
RULE: After each change, measure the app against the Spec's screen list; show pass/fail.
RULE: After each working step: run all tests, show me proof, commit, and push to GitHub.
RULE: When code and masterplan disagree, propose only major changes, one line each; update the masterplan after I approve.
RULE: Measure UI layout with pixels against reference measurements; never claim "matches" from a visual impression.
RULE: Keep the app responsive while it works, never stuck waiting on data or input.
RULE: Keep a short list of known limitations in the masterplan; update it as we go.
RULE: Run each stage without stopping; stop for my review only at stage end, on a failed test, or when you need my decision.
RULE: Test connections to outside data with real servers before building screens that depend on them.
RULE: Get a simple version running early, then add features one at a time, testing each.

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
  1a. Server band filter: after login, the server-side band filter command is sent and the server acknowledges it. The exact command and acknowledgement text are not in `idea.md`; they stay open until a live session, then are recorded in Tech. The filter asks for only the band containing the default frequency (20 m).
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
- The server-side band filter command and its acknowledgement text (see check 1a). The band requested is 20 m only; what happens when the operator sets a frequency on another band is not decided.

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

Every sub-step follows the Constitution: after each working step, run all tests, show proof, commit and push; after each change to the app, measure it against the Spec's screen list. A stage is not done until its "done when" line is shown as pass.

## Stage 1: Environment
- 1.1 Start-of-build check: Python, Tk, venv, pip, git identity, GitHub login and SSH (`ssh -T git@github.com`), and this folder's repo; show pass/fail for each. (Repo root and `origin` jcarter-labs/RSGB-3 are already set up and pushed.)
- 1.2 Create `./.venv`, install `requests`, `Pillow` and `pytest`, write the environment steps to `docs/setup.md`, add `.gitignore`; `pytest` runs with one trivial test.
- 1.3 Measure `screenshot.png` with a script and save the measurements to a file in this folder. All layout checks against the Spec's screen list use these measurements, not the approximate positions in the Spec.

Done when: every check in 1.1 passes, `pytest` runs inside the venv, and the measurements file gives a measured position and size for each of the 19 screen-list elements.

## Stage 2: Data connections
- 2.1 Save a live NC7J session: login prompt text, band filter command and its acknowledgement, and a raw capture of 50 lines or 5 minutes.
- 2.2 Save one live POTA.app response. Record both captures' findings in Tech's "Open until a live session" table, with the capture files named.
- 2.3 `cluster_parse` and `pota_parse`, tested on the saved captures.
- 2.4 `cluster_client` (socket worker thread, login, band filter, raw lines and status items on the queue, reconnect at 5, 10, 30 s then every 60 s).
- 2.5 `pota_client` (60 s poll, raw records on the queue, a status item on failure with old spots kept).
- 2.6 Test both clients against the live servers, including a forced disconnect and reconnect, a blocked network, and a POTA failure.
- 2.7 A bare window showing live RBN and POTA spots as two plain text lists (call, freq, age), fed through the queue. No bandmap, no layout, no styling, no client-side filtering; each list keeps only its last 50 entries, and the server-side band filter stays on, requesting only the band containing the default frequency (20 m). 2.7 depends on 2.1, which confirms the filter command. If 2.1 cannot confirm it, 2.7 drops off-band spots client-side and logs "server filter unconfirmed" until it is fixed. The window's `after()` tick drains the queue with a small temporary drain, which `app` replaces in 3.5.

Done when: both captures are saved and the Tech table is closed, each parser's accepted plus rejected equals the items read, and both clients pass the live checks, including reconnect with the retry count, and the bare window shows live spots in both lists within 60 s of starting.

## Stage 3: Core logic (offline tests on the captures)
- 3.1 `spot_filter` (skimmer match, client-side CW check, frequency range, POTA drops).
- 3.2 `settings` (frequency, bandwidth, window, Local/Regional; bad entry rejected, old value kept).
- 3.3 `spot_store` (age, linear opacity to 15%, drop past the window, counts, Clear), on a fake clock.
- 3.4 `layout` (frequency to position, label spreading of at least one text height, no Tk import).
- 3.5 `app` (`app.drain()` calls the parsers, filter and store and applies status items).

Done when: all offline tests pass with no network and no window, including the matching, non-matching and non-CW cases, and a crowded-labels case for `layout`; any shortfall is added to the known limitations list.

## Stage 4: Features
- 4.1 Controls wired to `settings` (Set, Bandwidth, Window, Spotter, Server, Clear), driven by the single `after()` tick that calls `app.drain()` then redraws.
- 4.2 Live RBN lane (left scale): blue call signs, leader lines, cluster status dot and retry count.
- 4.3 Live POTA lane (right scale): green call signs, ticks only, "last poll Ns ago".
- 4.4 Fading: to 15% over the window, dropped when older.
- 4.5 Local/Regional tier switching.
- 4.6 Click a call sign to copy it.

Done when: against live data, each feature behaves as in Spec Features (frequency, bandwidth and window limits, fade values, counts matching what is on screen, exactly the clicked call sign on the clipboard) and the window stays responsive.

## Stage 5: UI
- 5.1 Layout compared with the stage 1 measurements, pass/fail per screen-list element.
- 5.2 Resize: minimum 400 x 700, layout scales above it.
- 5.3 Full screen-list check, both source checks live, failure tests, responsiveness check; update the known limitations list.
- 5.4 One documented launch command, `docs/setup.md` complete, final test run, commit and push.

Done when: every screen-list element passes by measurement, every check above passes or is listed as a known limitation, and the app starts from a fresh clone using only `docs/setup.md`.
