# ha_zeroclaw_bridge

Home Assistant custom integration that connects **Assist** to a [ZeroClaw](https://github.com/zeroclaw-labs/zeroclaw) gateway via `POST /webhook`.

## Install

### With HACS (recommended)

1. In Home Assistant open **HACS** → **Integrations**.
2. Open the menu (⋮) → **Custom repositories**.
3. Add repository `https://github.com/holger81/ha_zeroclaw_bridge`, category **Integration**, then **Add**.
4. Search for **ZeroClaw Conversation**, open it, and choose **Download** (pick a release or the default branch).
5. Restart Home Assistant.
6. Add the integration **ZeroClaw Conversation** and enter your gateway base URL (e.g. `http://host:8585`), optional bearer token, and optional webhook secret.
7. Under **Settings → Voice assistants**, edit your Assist pipeline and choose this integration as the **conversation agent**.

### Manual

1. Copy `custom_components/zeroclaw_conversation` into your Home Assistant configuration directory (alongside `configuration.yaml`).
2. Restart Home Assistant.
3. Add the integration **ZeroClaw Conversation** and enter your gateway base URL (e.g. `http://host:8585`), optional bearer token, and optional webhook secret.
4. Under **Settings → Voice assistants**, edit your Assist pipeline and choose this integration as the **conversation agent**.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ruff
ruff check custom_components
```
