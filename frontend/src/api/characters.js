export async function listCharacters(campaignId) {
  const response = await fetch(`/api/campaigns/${campaignId}/characters`);
  if (!response.ok) throw new Error("Failed to load characters");
  return response.json();
}
