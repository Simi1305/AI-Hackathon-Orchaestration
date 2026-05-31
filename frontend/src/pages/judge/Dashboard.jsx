import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import HeroCard from "../../components/HeroCard";
import { fetchWithAuth, getRole } from "../../api";

const navItems = [
  {
    id: "dashboard",
    label: "Dashboard",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    id: "evaluations",
    label: "Evaluations",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16c0 1.1.9 2 2 2h12a2 2 0 0 0 2-2V8l-6-6z" />
        <path d="M14 3v5h5M16 13H8M16 17H8M10 9H8" />
      </svg>
    ),
  }
];

const pageContent = {
  dashboard: {
    title: "Judge Dashboard",
    description: "Overview of your pending evaluations and scoring metrics.",
  },
  evaluations: {
    title: "Evaluations",
    description: "Teams assigned to you for scoring.",
  },
};

export default function JudgeDashboard() {
  const [active, setActive] = useState("dashboard");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchWithAuth("/api/v1/judge/me");
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-400">Loading judge data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-rose-400">Error: {error}</div>
      </div>
    );
  }

  return (
    <DashboardLayout
      navItems={navItems}
      pageContent={pageContent}
      active={active}
      setActive={setActive}
      role="JUDGE"
      username={data?.name || "Judge"}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <HeroCard
          card={{
            id: "pending",
            title: "Pending Evaluations",
            value: data?.pending_evaluations?.length || 0,
            change: "Action required",
            up: false,
            footer: "Teams waiting for scores",
            iconWrapCls: "bg-rose-500/15",
            iconCls: "text-rose-400",
            borderHover: "hover:border-rose-500/40",
            alert: true,
            icon: (
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            )
          }}
        />
        <HeroCard
          card={{
            id: "expertise",
            title: "Expertise",
            value: data?.expertise || "General",
            change: "Your assigned track",
            up: true,
            footer: "Evaluation criteria",
            iconWrapCls: "bg-indigo-500/15",
            iconCls: "text-indigo-400",
            borderHover: "hover:border-indigo-500/40",
            dotColor: "#818cf8",
            spark: [20, 22, 24, 26, 28, 30, 32, 34],
            icon: (
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2l3 6h6l-4.5 4.5 1.5 6.5-6-3.5-6 3.5 1.5-6.5L2 8h6z" />
              </svg>
            )
          }}
        />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 className="text-lg font-medium text-white mb-6">Teams to Evaluate</h3>
        
        {data?.pending_evaluations?.length > 0 ? (
          <div className="grid grid-cols-1 gap-4">
            {data.pending_evaluations.map((team) => (
              <div key={team.id} className="p-4 bg-slate-800/50 rounded-xl border border-slate-700 flex justify-between items-center">
                <div>
                  <h4 className="font-semibold text-white">{team.name}</h4>
                  <p className="text-sm text-slate-400 mt-1">
                    Challenge: {team.challenge}
                  </p>
                </div>
                <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors">
                  Score Team
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            You have no pending evaluations.
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
