from datetime import datetime, timezone

_presence: dict[str, dict[str, str]] = {}


def touch(campaign_id: str, username: str) -> dict[str, str]:
    campaign = _presence.setdefault(campaign_id, {})
    campaign[username] = datetime.now(timezone.utc).isoformat()
    return campaign.copy()


def remove(campaign_id: str, username: str) -> dict[str, str]:
    campaign = _presence.setdefault(campaign_id, {})
    campaign.pop(username, None)
    return campaign.copy()


def list_presence(campaign_id: str) -> dict[str, str]:
    return _presence.get(campaign_id, {}).copy()
