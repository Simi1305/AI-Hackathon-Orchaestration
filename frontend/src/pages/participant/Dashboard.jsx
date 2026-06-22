import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import HeroCard from "../../components/HeroCard";
import { fetchWithAuth, getRole } from "../../api";

/* ── Nav items ── */
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
    id: "myteam",
    label: "My Team",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: "certificates",
    label: "Certificates",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
        <line x1="12" y1="22.08" x2="12" y2="12"></line>
      </svg>
    ),
  },
];

const pageContent = {
  dashboard: { title: "Dashboard", description: "Your participant hub — profile, team, and submissions at a glance." },
  myteam: { title: "My Team", description: "Chat with your teammates and mentor in real time." },
  submissions: { title: "Submissions", description: "Submit your project deliverables and track submission status." },
  certificates: { title: "Certificates", description: "View and download your participation certificates." },
};

const skillColors = [
  "bg-indigo-500/15 text-indigo-400 border-indigo-500/25",
  "bg-violet-500/15 text-violet-400 border-violet-500/25",
  "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
  "bg-amber-500/15 text-amber-400 border-amber-500/25",
  "bg-rose-500/15 text-rose-400 border-rose-500/25",
  "bg-cyan-500/15 text-cyan-400 border-cyan-500/25",
];

const avatarColors = [
  "from-violet-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-orange-600",
  "from-rose-500 to-pink-600",
  "from-cyan-500 to-blue-600",
];

export default function ParticipantDashboard() {
  const [active, setActive] = useState("dashboard");
  const [data, setData] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [presentationUrl, setPresentationUrl] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitMsg, setSubmitMsg] = useState("");
  
  // Chat state
  const [chatData, setChatData] = useState(null);
  const [chatMsg, setChatMsg] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [certificates, setCertificates] = useState([]);
  const [announcements, setAnnouncements] = useState([]);

  useEffect(() => {
    async function fetchData() {
      try {
        const d = await fetchWithAuth("/api/v1/participant/me");
        if (d) setData(d);
      } catch (err) {
        console.error("Failed to fetch participant data:", err);
      }
    }
    
    async function fetchChat() {
      try {
        const c = await fetchWithAuth("/api/v1/team/chat");
        if (c) setChatData(c);
      } catch (err) {
        console.error("Failed to fetch chat:", err);
      }
    }
    
    async function fetchCertificates() {
      try {
        const c = await fetchWithAuth("/api/v1/participant/certificates");
        if (c) setCertificates(c);
      } catch (err) {
        console.error("Failed to fetch certificates:", err);
      }
    }

    async function fetchAnnouncements() {
      try {
        const n = await fetchWithAuth("/api/v1/notifications");
        if (n) setAnnouncements(n);
      } catch (err) {
        console.error("Failed to fetch announcements:", err);
      }
    }

    fetchData();
    fetchChat();
    fetchAnnouncements();
    fetchCertificates();
    
    // Simple polling for chat
    const interval = setInterval(fetchChat, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSendChat = async () => {
    if (!chatMsg.trim()) return;
    setChatSending(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/team/chat/send", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({ content: chatMsg }),
      });
      if (res.ok) {
        setChatMsg("");
        // Optimistically reload chat
        const c = await fetchWithAuth("/api/v1/team/chat");
        if (c) setChatData(c);
      }
    } catch (err) {
      console.error("Failed to send message", err);
    } finally {
      setChatSending(false);
    }
  };

  const skillsList = data?.skills ? (typeof data.skills === "string" ? data.skills.split(",").map(s => s.trim()) : data.skills) : [];
  const teamMembers = data?.team_members || [];

  const heroCards = [
    {
      id: "team-status",
      title: "Team Status",
      value: data?.team_id ? "Assigned" : "Pending",
      change: data?.team_id ? `Team #${data.team_id}` : "Awaiting formation",
      up: !!data?.team_id,
      footer: data?.team_id ? "You've been placed on a team" : "Team formation in progress",
      iconWrapCls: data?.team_id ? "bg-emerald-500/15" : "bg-emerald-500/15",
      iconCls: data?.team_id ? "text-emerald-400" : "text-amber-400",
      borderHover: data?.team_id ? "hover:border-emerald-500/40" : "hover:border-amber-500/40",
      dotColor: data?.team_id ? "#34d399" : "#fbbf24",
      spark: [30, 35, 40, 45, 50, 55, 60, 65],
      icon: (
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      id: "submission",
      title: "Submission Status",
      value: data?.submission_status || "Not Submitted",
      change: "Action required",
      up: false,
      footer: "Project deliverables pending",
      iconWrapCls: "bg-rose-500/15",
      iconCls: "text-rose-400",
      borderHover: "hover:border-rose-500/40",
      dotColor: "#fb7185",
      spark: [10, 12, 14, 15, 12, 15, 18, 20],
      icon: (
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      ),
    },
  ];

  return (
    <DashboardLayout
      role="PARTICIPANT"
      navItems={navItems}
      active={active}
      setActive={setActive}
      pageContent={pageContent}
    >
      {active === "dashboard" && (
        <>
          {/* Top Hero Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {heroCards.map((c) => (
              <HeroCard key={c.id} card={c} />
            ))}
          </div>

          {/* Event Status: stage, evaluator, key dates */}
          {data && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
              <h3 className="text-lg font-medium text-white mb-5">Event Status</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                <div>
                  <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1.5">Current Stage</label>
                  <span className="inline-block px-3 py-1 rounded-lg bg-indigo-500/15 text-indigo-300 text-[13px] font-semibold">
                    {(data.current_stage || "SETUP").replace(/_/g, " ")}
                  </span>
                </div>
                <div>
                  <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1.5">Your Evaluator</label>
                  <div className="text-slate-200 text-[14px]">{data.evaluator_name || "To be assigned"}</div>
                </div>
                <div>
                  <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1.5">Key Dates</label>
                  <div className="space-y-1">
                    {(data.key_dates || []).map((kd, i) => (
                      <div key={i} className="flex justify-between text-[13px]">
                        <span className="text-slate-400">{kd.label}</span>
                        <span className="text-slate-300 font-medium">{kd.date}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Announcements: messages the organizer sent to participants */}
          {announcements.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
              <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-400 inline-block"></span>
                Announcements
              </h3>
              <div className="space-y-3">
                {announcements.slice(0, 8).map((a) => (
                  <div key={a.id} className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/60">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white font-medium text-[14px]">{a.title}</span>
                      <span className="text-slate-500 text-[11px]">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</span>
                    </div>
                    <p className="text-slate-400 text-[13px] leading-relaxed whitespace-pre-line">{a.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Profile Overview */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-medium text-white mb-6">My Profile</h3>
              {data ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Name</label>
                    <div className="text-slate-200 text-[15px]">{data.name}</div>
                  </div>
                  <div>
                    <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Institution</label>
                    <div className="text-slate-200 text-[15px]">{data.institution}</div>
                  </div>
                  <div>
                    <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">Skills</label>
                    <div className="flex flex-wrap gap-2">
                      {skillsList.map((skill, idx) => (
                        <span key={idx} className={`px-2.5 py-1 rounded-md text-[12px] font-medium border ${skillColors[idx % skillColors.length]}`}>
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 text-sm">Loading profile...</div>
              )}
            </div>

            {/* Team Details & Mentor Info */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-lg font-medium text-white mb-6">Team & Mentor</h3>
              {data?.team_id ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/15 flex items-center justify-center text-indigo-400">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                          <circle cx="9" cy="7" r="4" />
                          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                        </svg>
                      </div>
                      <div>
                        <h4 className="text-white font-medium text-[15px]">{data.team_name}</h4>
                        <div className="text-slate-400 text-[13px]">Team #{data.team_id}</div>
                      </div>
                    </div>
                    
                    {data.compatibility_score !== undefined && (
                      <div className="mb-4">
                        <div className="flex justify-between items-end mb-1.5">
                          <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Synergy Score</span>
                          <span className="text-indigo-400 text-sm font-semibold">{Math.round(data.compatibility_score * 100)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 rounded-full" 
                            style={{ width: `${Math.round(data.compatibility_score * 100)}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    <div className="space-y-2.5">
                      <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Members</label>
                      {teamMembers.map((member, i) => (
                        <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 transition-colors">
                          <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${avatarColors[i % avatarColors.length]} flex items-center justify-center text-white text-[13px] font-bold shadow-lg`}>
                            {member.name.charAt(0)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-slate-200 text-[13.5px] font-medium truncate">{member.name}</div>
                            <div className="text-slate-500 text-[12px] truncate">{member.skills}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {data.mentor_name && (
                    <div className="pt-4 border-t border-slate-800/50">
                      <label className="block text-slate-500 text-xs font-semibold uppercase tracking-wider mb-3">Assigned Mentor</label>
                      <div className="flex items-start gap-3 p-3 bg-indigo-500/5 border border-indigo-500/10 rounded-xl">
                        <div className="w-9 h-9 rounded-full bg-indigo-500/15 flex items-center justify-center text-indigo-400 flex-shrink-0">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                          </svg>
                        </div>
                        <div>
                          <div className="text-indigo-300 font-medium text-[14px]">{data.mentor_name}</div>
                          <div className="text-indigo-400/70 text-[12.5px] leading-relaxed mt-0.5">{data.mentor_expertise}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-500/50 mb-3">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <p className="text-slate-400 text-[14px] font-medium">Team formation pending</p>
                  <p className="text-slate-500 text-[12.5px] mt-1 max-w-[200px]">You will be assigned a team shortly by the organizers.</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {active === "submissions" && (
        <div className="max-w-2xl">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-white font-semibold text-[16px] mb-1">Submit Your Project</h2>
            <p className="text-slate-500 text-[12.5px] mb-6">Provide links to your project repository and presentation</p>

            <div className="space-y-4">
              <div>
                <label className="block text-slate-400 text-[12px] font-semibold uppercase tracking-wider mb-2">GitHub Repository URL</label>
                <input
                  type="url"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/your-team/project"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-[13.5px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 text-[12px] font-semibold uppercase tracking-wider mb-2">Presentation URL</label>
                <input
                  type="url"
                  value={presentationUrl}
                  onChange={(e) => setPresentationUrl(e.target.value)}
                  placeholder="https://docs.google.com/presentation/..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-[13.5px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-200"
                />
              </div>

              {submitMsg && (
                <div className={`flex items-center gap-2 text-[12.5px] font-medium rounded-xl px-4 py-2.5 ${submitMsg.includes("success") ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400" : "bg-rose-500/10 border border-rose-500/20 text-rose-400"}`}>
                  {submitMsg}
                </div>
              )}

              <button
                onClick={async () => {
                  setSubmitLoading(true);
                  setSubmitMsg("");
                  try {
                    // Placeholder API call
                    setSubmitMsg("Submission saved successfully!");
                  } catch {
                    setSubmitMsg("Failed to submit. Try again.");
                  } finally {
                    setSubmitLoading(false);
                  }
                }}
                disabled={submitLoading || !githubUrl}
                className="w-full py-3 rounded-xl text-white font-semibold text-[14px] bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-indigo-500/20"
              >
                {submitLoading ? "Submitting..." : "Submit Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Team Chat Section */}
      {active === "myteam" && (
        <div className="max-w-4xl mx-auto h-[70vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur-md flex items-center justify-between">
            <div>
              <h2 className="text-white font-semibold text-[16px]">Team Chat</h2>
              <p className="text-slate-500 text-[12px]">Chat with your teammates and mentor</p>
            </div>
            <div className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-[11px] font-medium">
              Live
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-900/30">
            {chatData?.messages?.length > 0 ? (
              chatData.messages.map((msg) => (
                <div key={msg.id} className={`flex flex-col ${msg.sender_name === localStorage.getItem("username") ? "items-end" : "items-start"}`}>
                  <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-[12px] font-medium text-slate-300">{msg.sender_name}</span>
                    <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-md ${msg.sender_role === "MENTOR" ? "bg-indigo-500/20 text-indigo-400" : "bg-slate-800 text-slate-400"}`}>
                      {msg.sender_role}
                    </span>
                    <span className="text-[10px] text-slate-600">{new Date(msg.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  </div>
                  <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-[14px] ${msg.sender_name === localStorage.getItem("username") ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-slate-800 border border-slate-700 text-slate-200 rounded-tl-sm"}`}>
                    {msg.content}
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-[13px]">
                No messages yet. Say hello!
              </div>
            )}
          </div>
          
          <div className="p-4 border-t border-slate-800 bg-slate-900/80">
            <div className="flex gap-3">
              <input
                type="text"
                value={chatMsg}
                onChange={(e) => setChatMsg(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                placeholder="Type your message..."
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white text-[13.5px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              />
              <button
                onClick={handleSendChat}
                disabled={chatSending || !chatMsg.trim()}
                className="px-5 py-3 rounded-xl text-white font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition-all flex items-center justify-center"
              >
                {chatSending ? "..." : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {active === "certificates" && (
        <div className="max-w-4xl mx-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-white font-semibold text-[16px] mb-1">My Certificates</h2>
            <p className="text-slate-500 text-[12.5px] mb-6">Download your officially issued hackathon certificates.</p>

            {certificates.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {certificates.map((cert) => (
                  <div key={cert.id} className="p-5 border border-slate-700 bg-slate-800/40 rounded-xl flex flex-col items-center justify-center text-center hover:border-indigo-500/50 transition-colors">
                    <div className="w-14 h-14 bg-indigo-500/10 text-indigo-400 rounded-full flex items-center justify-center mb-4 border border-indigo-500/20">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                      </svg>
                    </div>
                    <h3 className="text-white font-medium text-[15px] mb-1">{cert.certificate_type} Certificate</h3>
                    <p className="text-slate-400 text-[12px] mb-5">Issued: {new Date(cert.issued_at).toLocaleDateString()}</p>
                    <a 
                      href={cert.download_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="w-full py-2.5 rounded-lg text-white font-medium text-[13px] bg-indigo-600 hover:bg-indigo-500 transition-colors block"
                    >
                      Download PDF
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-slate-700 rounded-xl bg-slate-800/20">
                <div className="w-12 h-12 bg-slate-800 text-slate-500 rounded-full flex items-center justify-center mb-3">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                  </svg>
                </div>
                <h3 className="text-slate-300 font-medium text-[14px] mb-1">No Certificates Found</h3>
                <p className="text-slate-500 text-[12.5px] max-w-sm">
                  Your certificates will appear here once the event concludes and the organizers publish them.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
