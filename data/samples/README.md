# Demo media fixtures

No real-person media or pre-labeled authenticity samples are bundled. The analyzer does not contain scripted demo verdicts: each displayed result must come from the uploaded file's actual evidence and, when configured, a live Gemini API response.

For a responsible live demo, add three locally sourced, rights-cleared short samples here and record their source and limitations in a local notes file (do not commit private media):

1. `consistent` — an ordinary image/video with a known capture context and, ideally, original camera metadata or verifiable provenance.
2. `high-risk` — a rights-cleared example with independently documented manipulation, plus a source note. The result may still be uncertain; do not tune the system to force a state.
3. `ambiguous` — a sample whose provenance is unavailable or whose documented signals disagree. This is a useful uncertainty/conflict demonstration.

The root `.gitignore` excludes files in this directory other than this README to help prevent accidental media commits.
