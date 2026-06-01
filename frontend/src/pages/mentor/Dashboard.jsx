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

  // Chat state
  const [chatData, setChatData] = useState([]);
  const [chatMsgs, setChatMsgs] = useState({});
  const [chatSending, setChatSending] = useState(false);

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
    
    async function loadChats() {
      try {
        const result = await fetchWithAuth("/api/v1/mentor/chat");
        if (result) setChatData(result);
      } catch (err) {
        console.error("Failed to load chats:", err);
      }
    }
    
    loadData();
    loadChats();
    
    const interval = setInterval(loadChats, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSendChat = async (teamId) => {
    const msg = chatMsgs[teamId];
    if (!msg || !msg.trim()) return;
    
    setChatSending(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/mentor/chat/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({ content: msg, team_id: teamId }),
      });
      if (res.ok) {
        setChatMsgs(prev => ({ ...prev, [teamId]: "" }));
        const c = await fetchWithAuth("/api/v1/mentor/chat");
        if (c) setChatData(c);
      }
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setChatSending(false);
    }
  };

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
      {active === "dashboard" && (
        <>
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
        </>
      )}

      {active === "my-teams" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-lg font-medium text-white mb-6">Team Conversations</h3>
          {data?.assigned_teams?.length > 0 ? (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {data.assigned_teams.map((team) => {
                const conv = chatData?.find(c => c.team_id === team.id);
                const messages = conv?.messages || [];
                return (
                  <div key={team.id} className="flex flex-col h-[60vh] bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden shadow-lg">
                    <div className="p-4 border-b border-slate-700/50 bg-slate-800/50 flex items-center justify-between">
                      <div>
                        <h4 className="text-white font-semibold text-[15px]">{team.name}</h4>
                        <p className="text-slate-400 text-[11px] truncate max-w-[200px]">{team.challenge.split('|')[0]}</p>
                      </div>
                      <div className="px-2.5 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full text-[10px] font-medium">
                        Team #{team.id}
                      </div>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                      {messages.length > 0 ? (
                        messages.map((msg) => (
                          <div key={msg.id} className={`flex flex-col ${msg.sender_name === localStorage.getItem("username") ? "items-end" : "items-start"}`}>
                            <div className="flex items-center gap-1.5 mb-1 px-1">
                              <span className="text-[11px] font-medium text-slate-300">{msg.sender_name}</span>
                              <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded ${msg.sender_role === "PARTICIPANT" ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-700 text-slate-400"}`}>
                                {msg.sender_role}
                              </span>
                              <span className="text-[9px] text-slate-600">{new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                            </div>
                            <div className={`max-w-[85%] px-3 py-2 rounded-xl text-[13px] ${msg.sender_name === localStorage.getItem("username") ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-slate-700 text-slate-200 rounded-tl-sm"}`}>
                              {msg.content}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="flex items-center justify-center h-full text-slate-500 text-[12px]">
                          No messages yet.
                        </div>
                      )}
                    </div>
                    
                    <div className="p-3 border-t border-slate-700/50 bg-slate-800/50">
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={chatMsgs[team.id] || ""}
                          onChange={(e) => setChatMsgs(prev => ({ ...prev, [team.id]: e.target.value }))}
                          onKeyDown={(e) => e.key === "Enter" && handleSendChat(team.id)}
                          placeholder="Reply to team..."
                          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white text-[13px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all"
                        />
                        <button
                          onClick={() => handleSendChat(team.id)}
                          disabled={chatSending || !(chatMsgs[team.id] || "").trim()}
                          className="px-4 py-2 rounded-lg text-white font-medium text-[13px] bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition-all"
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-10 text-slate-400">
              You are not assigned to any teams yet.
            </div>
          )}
        </div>
      )}
    </DashboardLayout>
  );
}
