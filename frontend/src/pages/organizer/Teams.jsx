import { useState, useEffect } from "react";
import { fetchWithAuth } from "../../api";

function initials(name) {
  return (name || "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWithAuth("/api/v1/teams/")
      .then((d) => d && setTeams(d))
      .catch((e) => console.error("Failed to load teams:", e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-slate-400 text-sm">
        Loading teams...
      </div>
    );
  }

  if (teams.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center text-slate-400 text-sm">
        No teams formed yet. Run team formation from the dashboard.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-white font-semibold text-[15px]">Formed Teams</h3>
          <p className="text-slate-500 text-[13px] mt-1">
            AI-balanced teams with a generated rationale for each grouping.
          </p>
        </div>
        <span className="px-3 py-1 rounded-lg bg-violet-500/10 text-violet-300 text-[12px] font-semibold">
          {teams.length} teams
        </span>
      </div>

      {teams.map((team) => (
        <div key={team.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-3">
                <h4 className="text-white font-semibold text-[15px]">{team.name}</h4>
                <span className="px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 text-[11px]">
                  Team #{team.id}
                </span>
                {team.is_approved ? (
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 text-[11px]">
                    Approved
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 text-[11px]">
                    Pending approval
                  </span>
                )}
              </div>
              {team.challenge && (
                <p className="text-slate-500 text-[12px] mt-1">
                  Challenge: {team.challenge}
                </p>
              )}
            </div>
            {team.final_score != null && (
              <div className="text-right">
                <div className="text-white font-semibold text-[15px]">{team.final_score}</div>
                <div className="text-slate-500 text-[11px]">
                  {team.rank ? `Rank #${team.rank}` : "Final score"}
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Members */}
            <div>
              <h5 className="text-slate-400 text-[11px] uppercase mb-3">
                Members ({team.members?.length || 0})
              </h5>
              <div className="space-y-3">
                {(team.members || []).map((m) => (
                  <div key={m.id} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-[11px] font-semibold flex-shrink-0">
                      {initials(m.name)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-white text-[13px] font-medium">
                        {m.name}
                        <span className="text-slate-500 text-[11px] ml-2 capitalize">{m.experience}</span>
                      </div>
                      <div className="text-slate-500 text-[11px]">{m.institution}</div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {(m.skill_tags || "").split(",").filter(Boolean).map((s, i) => (
                          <span key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                            {s.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI rationale */}
            <div>
              <h5 className="text-slate-400 text-[11px] uppercase mb-3 flex items-center gap-1.5">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                AI rationale
              </h5>
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 text-slate-300 text-[12.5px] leading-relaxed">
                {team.rationale || "Rationale is being generated..."}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
