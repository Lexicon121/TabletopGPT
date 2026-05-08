export function connectCampaignSocket(campaignId, username) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${window.location.host}/ws/${campaignId}/${encodeURIComponent(username)}`);
}
