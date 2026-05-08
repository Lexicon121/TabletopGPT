import CampaignList from "./components/CampaignList.jsx";
import CampaignLobby from "./components/CampaignLobby.jsx";
import LiveSession from "./components/LiveSession.jsx";

export default function App() {
  return (
    <main>
      <h1>TabletopGPT</h1>
      <CampaignList />
      <CampaignLobby />
      <LiveSession />
    </main>
  );
}
