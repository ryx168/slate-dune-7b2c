# Seedance 2.0 on GitHub Actions

Renders short photoreal clips with ByteDance's Seedance 2.0 through BytePlus ModelArk,
in the style of x.com/minchoi/status/2021372081359712555 (a 51 s Dragon Ball fan film:
Cell, Buu, Android 18 and Vegeta on a ruined highway). `prompts/` rebuilds that look
shot-for-shot with original characters so moderation does not refuse trademarked ones.

## One-time setup (repo owner)
1. BytePlus account at https://console.byteplus.com, verified.
2. Buy a Seedance 2.0 resource pack in ModelArk. The 2M free video tokens a new
   account gets do NOT cover Seedance 2.0; the 2.0 models only activate while a
   pack with remaining quota exists (BytePlus also asks for USD 30+ balance).
3. Activate the Seedance 2.0 models in ModelArk, create a key at
   https://ai.byteplus.com/ark/region:ap-southeast-1/apikey
4. Repo secret `ARK_API_KEY` (Settings > Secrets and variables > Actions).

Without the secret the workflow prints the plan and price and spends nothing.

## Run
Actions > seedance > Run workflow, or:
```
gh workflow run seedance.yml -R ryx168/slate-dune-7b2c -f prompt=all -f model=mini -f resolution=720p -f duration=10 -f audio=true -f ratio=16:9
# optional: -f refs="https://.../hero.png,https://.../villain.png"  (Image 1, Image 2 in the prompt)
```
Output: artifact `seedance-run-<n>` and release `run-<n>` with the clips and `film.mp4`.

## Cost per 10 s clip, 16:9 (list price, verified 2026-10-06)
| model | 480p | 720p | 1080p |
|---|---|---|---|
| mini | $0.40 | $0.80 | n/a |
| fast | $0.70 | $1.50 | n/a |
| std (2.0) | $0.70 | $1.50 | $3.70 |
| 2.5 | $1.03 | $2.31 | $5.69 |

All three prompts: about $2.40 at mini 720p, about $11 at std 1080p.

Locally: `python run_seedance.py prompts/shot1_villain_reveal.txt --audio --execute`
(key from `ARK_API_KEY` or `%APPDATA%/agent-sprite-forge/config.json`).
