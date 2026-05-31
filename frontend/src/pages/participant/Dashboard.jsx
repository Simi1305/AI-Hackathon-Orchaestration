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
    id: "submissions",
    label: "Submissions",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
];

const pageContent = {
  dashboard: { title: "Dashboard", description: "Your participant hub — profile, team, and submissions at a glance." },
  myteam: { title: "My Team", description: "View your team composition, members, and compatibility details." },
  submissions: { title: "Submissions", description: "Submit your project deliverables and track submission status." },
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

  useEffect(() => {
    async function fetchData() {
      try {
        const d = await fetchWithAuth("/api/v1/participant/me");
        if (d) setData(d);
      } catch (err) {
        console.error("Failed to fetch participant data:", err);
      }
    }
    fetchData();
  }, []);

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
      iconWrapCls: data?.team_id ? "bg-emerald-500/15" : "bg-amber-500/15",
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
      change: data?.submission_status === "submitted" ? "Submitted" : "Awaiting",
      up: data?.submission_status === "submitted",
      footer: "Project deliverables",
      iconWrapCls: "bg-violet-500/15",
      iconCls: "text-violet-400",
      borderHover: "hover:border-violet-500/40",
      dotColor: "#a78bfa",
      spark: [10, 15, 20, 25, 30, 35, 40, 45],
      icon: (
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      ),
    },
    {
      id: "mentor",
      title: "Mentor",
      value: data?.mentor_name || "Unassigned",
      change: data?.mentor_name ? "Assigned" : "Pending",
      up: !!data?.mentor_name,
      footer: "Your team's mentor",
      iconWrapCls: "bg-indigo-500/15",
      iconCls: "text-indigo-400",
      borderHover: "hover:border-indigo-500/40",
      dotColor: "#818cf8",
      spark: [20, 22, 24, 26, 28, 30, 32, 34],
      icon: (
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
        </svg>
      ),
    },
    {
      id: "synergy",
      title: "Team Synergy",
      value: data?.synergy_score ? `${data.synergy_score}%` : "N/A",
      change: data?.synergy_score >= 80 ? "Excellent" : data?.synergy_score >= 60 ? "Good" : "Building",
      up: (data?.synergy_score || 0) >= 60,
      footer: "AI-computed compatibility",
      iconWrapCls: "bg-emerald-500/15",
      iconCls: "text-emerald-400",
      borderHover: "hover:border-emerald-500/40",
      dotColor: "#34d399",
      spark: [50, 55, 60, 65, 70, 75, 80, 85],
      icon: (
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
  ];

  return (
    <DashboardLayout navItems={navItems} pageContent={pageContent} active={active} setActive={setActive} role={getRole()}>
      {active === "dashboard" && (
        <>
          {/* Hero Cards */}
          <section className="mb-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-60" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500" />
              </span>
              <p className="text-slate-400 text-[12px] font-medium">Participant Hub</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {heroCards.map((card) => (
                <HeroCard key={card.id} card={card} />
              ))}
            </div>
          </section>

          {/* Profile Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <span className="text-white text-sm font-bold">{(data?.name || "U").slice(0, 2).toUpperCase()}</span>
                </div>
                <div>
                  <h2 className="text-white font-semibold text-[15px]">{data?.name || "Loading..."}</h2>
                  <p className="text-slate-500 text-[12px]">{data?.institution || "Institution not set"}</p>
                </div>
                <div className="ml-auto">
                  <span className="inline-flex items-center gap-1.5 text-[10.5px] font-semibold px-2.5 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/25 text-indigo-400">
                    {data?.experience_level || "Intermediate"}
                  </span>
                </div>
              </div>

              <div className="border-t border-slate-800 pt-4">
                <p className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider mb-2.5">Skills</p>
                <div className="flex flex-wrap gap-2">
                  {skillsList.length > 0 ? skillsList.map((skill, i) => (
                    <span
                      key={i}
                      className={`text-[11px] font-medium px-2.5 py-1 rounded-lg border ${skillColors[i % skillColors.length]}`}
                    >
                      {skill}
                    </span>
                  )) : (
                    <span className="text-slate-600 text-[12px]">No skills listed</span>
                  )}
                </div>
              </div>
            </div>

            {/* My Team Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-white font-semibold text-[15px]">
                    {data?.team_name || "My Team"}
                  </h2>
                  <p className="text-slate-500 text-[12px] mt-0.5">
                    {data?.team_id ? `Team #${data.team_id}` : "Not yet assigned to a team"}
                  </p>
                </div>
                {data?.compatibility_score && (
                  <div className="text-right">
                    <p className="text-emerald-400 text-[20px] font-bold">{data.compatibility_score}%</p>
                    <p className="text-slate-500 text-[10px]">Compatibility</p>
                  </div>
                )}
              </div>

              {teamMembers.length > 0 ? (
                <div className="space-y-2.5">
                  {teamMembers.map((member, i) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                      <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${avatarColors[i % avatarColors.length]} flex items-center justify-center flex-shrink-0`}>
                        <span className="text-white text-[10px] font-bold">{(member.name || "?").slice(0, 2).toUpperCase()}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-slate-200 text-[12.5px] font-medium truncate">{member.name}</p>
                        <p className="text-slate-500 text-[11px] truncate">{member.skills || "No skills listed"}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center mb-3">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <p className="text-amber-400 text-[13px] font-semibold">Team Formation Pending</p>
                  <p className="text-slate-500 text-[11.5px] mt-1">AI-powered team formation runs periodically</p>
                </div>
              )}
            </div>
          </div>

          {/* Assigned Mentor */}
          {data?.mentor_name && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-4">
              <h3 className="text-white font-semibold text-[14px] mb-3">Assigned Mentor</h3>
              <div className="flex items-center gap-4 p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                <div className="w-11 h-11 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-md">
                  <span className="text-white text-[12px] font-bold">{data.mentor_name.slice(0, 2).toUpperCase()}</span>
                </div>
                <div className="flex-1">
                  <p className="text-slate-200 text-[13px] font-semibold">{data.mentor_name}</p>
                  <p className="text-slate-500 text-[11.5px] mt-0.5">{data.mentor_expertise || "General mentoring"}</p>
                </div>
                <span className="text-[10.5px] font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 text-emerald-400">
                  Active
                </span>
              </div>
            </div>
          )}
        </>
      )}

      {/* Submissions Page */}
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

      {/* My Team placeholder */}
      {active === "myteam" && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-16 h-16 rounded-2xl bg-violet-500/15 text-violet-400 flex items-center justify-center mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h2 className="text-white font-semibold text-lg mb-1">My Team</h2>
          <p className="text-slate-500 text-[13px]">Detailed team view coming soon...</p>
        </div>
      )}
    </DashboardLayout>
  );
}
