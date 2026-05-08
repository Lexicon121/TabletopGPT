# API

This is a starter API surface. Payloads are intentionally small and will evolve.

## HTTP

- `GET /`: static app shell.
- `GET /health`: service health.
- `GET /api/campaigns`: list public campaigns.
- `POST /api/campaigns`: create a campaign.
- `POST /api/campaigns/{campaign_id}/join`: join a campaign.
- `POST /api/campaigns/{campaign_id}/characters`: create a character.
- `GET /api/campaigns/{campaign_id}/characters`: list campaign characters.
- `GET /api/campaigns/{campaign_id}/catchup/{username}`: get recent events and unread status.
- `POST /api/campaigns/{campaign_id}/resolve-round`: enqueue round resolution.
- `POST /api/campaigns/{campaign_id}/dm-mode`: update DM mode.
- `POST /api/campaigns/{campaign_id}/ask`: read-only Ask the DM endpoint.
- `POST /api/campaigns/{campaign_id}/gm-takeover-key`: generate an emergency takeover key.
- `POST /api/campaigns/{campaign_id}/claim-gm`: claim emergency takeover.
- `POST /api/campaigns/{campaign_id}/human-gm/resolve-round`: write human GM narration.

## WebSocket

- `WEBSOCKET /ws/{campaign_id}/{username}`

Supported starter message types:

- `official_action`
- `party_chat`
- `presence`

Official actions affect a future resolved round only after backend validation. Party chat and presence do not create official game events.
