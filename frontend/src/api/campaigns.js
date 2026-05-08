export async function listCampaigns() {
  const response = await fetch("/api/campaigns");
  if (!response.ok) throw new Error("Failed to load campaigns");
  return response.json();
}
