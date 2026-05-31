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
    id: "my-teams",
    label: "My Teams",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  }
];

const pageContent = {
  dashboard: {
    title: "Mentor Dashboard",
    description: "Welcome! Here you can see the teams you are mentoring.",
  },
  "my-teams": {
    title: "My Teams",
    description: "Teams assigned to you for mentoring.",
  },
};

export default function MentorDashboard() {
  const [active, setActive] = useState("dashboard");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchWithAuth("/api/v1/mentor/me");
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
        <div className="text-slate-400">Loading mentor data...</div>
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
      role="MENTOR"
      username={data?.name || "Mentor"}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <HeroCard
          card={{
            id: "assigned",
            title: "Assigned Teams",
            value: data?.assigned_teams?.length || 0,
            change: "+1 this week",
            up: true,
            footer: "Teams under your guidance",
            iconWrapCls: "bg-emerald-500/15",
            iconCls: "text-emerald-400",
            borderHover: "hover:border-emerald-500/40",
            dotColor: "#34d399",
            spark: [20, 22, 24, 26, 28, 30, 32, 34],
            icon: (
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            )
          }}
        />
        <HeroCard
          card={{
            id: "capacity",
            title: "Mentoring Capacity",
            value: `${data?.assigned_teams?.length || 0} / ${data?.capacity || 3}`,
            change: "Available",
            up: true,
            footer: "Your current workload",
            iconWrapCls: "bg-indigo-500/15",
            iconCls: "text-indigo-400",
            borderHover: "hover:border-indigo-500/40",
            dotColor: "#818cf8",
            spark: [10, 15, 20, 25, 30, 35, 40, 45],
            icon: (
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="8" r="4" />
              </svg>
            )
          }}
        />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 className="text-lg font-medium text-white mb-6">Teams You Are Mentoring</h3>
        
        {data?.assigned_teams?.length > 0 ? (
          <div className="grid grid-cols-1 gap-4">
            {data.assigned_teams.map((team) => (
              <div key={team.id} className="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-white">{team.name}</h4>
                  <span className="px-2 py-1 bg-indigo-500/10 text-indigo-400 text-xs rounded-md">
                    Team #{team.id}
                  </span>
                </div>
                <p className="text-sm text-slate-400 mb-2">
                  <strong>Challenge:</strong> {team.challenge}
                </p>
                <div className="text-xs text-slate-500">
                  Formed on {new Date(team.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            You have not been assigned any teams yet.
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
