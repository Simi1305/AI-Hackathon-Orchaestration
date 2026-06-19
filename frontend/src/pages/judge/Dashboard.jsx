import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import HeroCard from "../../components/HeroCard";
import { fetchWithAuth, postWithAuth, getRole } from "../../api";

const navItems = [
  {
    id: "dashboard",
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
    title: "Judge Evaluations",
    description: "Review AI briefs and score the teams assigned to you.",
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

  // AI Assistant state
  const [activeTeamId, setActiveTeamId] = useState(null);
  const [briefData, setBriefData] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  
  // Scoring state
  const [scoringData, setScoringData] = useState({
    innovation: 5.0,
    technical_depth: 5.0,
    presentation: 5.0,
    feasibility: 5.0,
    impact: 5.0,
  });
  const [submittingScore, setSubmittingScore] = useState(false);
  const [scoreSuccess, setScoreSuccess] = useState(false);
  const [scoreError, setScoreError] = useState("");

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

  const handleScoreTeam = async (teamId) => {
    if (activeTeamId === teamId) {
      setActiveTeamId(null);
      return;
    }
    setActiveTeamId(teamId);
    setBriefData(null);
    setBriefLoading(true);
    setScoreSuccess(false);
    setScoringData({
      innovation: 5.0,
      technical_depth: 5.0,
      presentation: 5.0,
      feasibility: 5.0,
      impact: 5.0,
    });
    try {
      const res = await fetchWithAuth(`/api/v1/judge/teams/${teamId}/brief`);
      if (res) setBriefData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setBriefLoading(false);
    }
  };

  const handleScoreChange = (field, value) => {
    setScoringData(prev => ({ ...prev, [field]: parseFloat(value) }));
  };

  const handleSubmitScore = async (teamId) => {
    setSubmittingScore(true);
    setScoreError("");
    try {
      await postWithAuth(`/api/v1/judge/teams/${teamId}/score`, scoringData);
      setScoreSuccess(true);
      // Optional: Refresh pending evaluations list
      const result = await fetchWithAuth("/api/v1/judge/me");
      setData(result);
      setTimeout(() => {
        setActiveTeamId(null);
      }, 1500);
    } catch (err) {
      console.error(err);
      setScoreError("Failed to submit score. Please try again.");
    } finally {
      setSubmittingScore(false);
    }
  };

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
            dotColor: "#fb7185",
            spark: [10, 15, 20, 25, 30, 35, 40, 45],
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
              <div key={team.id} className="p-4 bg-slate-800/50 rounded-xl border border-slate-700 flex flex-col">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-semibold text-white">{team.name}</h4>
                    <p className="text-sm text-slate-400 mt-1">
                      Challenge: {team.challenge}
                    </p>
                  </div>
                  <button 
                    onClick={() => handleScoreTeam(team.id)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {activeTeamId === team.id ? "Close" : "Score Team"}
                  </button>
                </div>

                {activeTeamId === team.id && (
                  <div className="mt-6 border-t border-slate-700 pt-6 space-y-10">
                    
                    {/* SECTION 1: PROJECT SUBMISSION */}
                    <div>
                      <div className="flex items-center gap-2 mb-6">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                            <polyline points="10 9 9 9 8 9" />
                          </svg>
                        </div>
                        <h5 className="text-white font-medium">Project Submission</h5>
                      </div>
                      
                      {briefLoading ? (
                        <div className="text-slate-400 text-sm animate-pulse">Loading submission data...</div>
                      ) : briefData?.submission ? (
                        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-5 space-y-6">
                          <div>
                            <h6 className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-1">Project Name</h6>
                            <p className="text-white text-lg font-medium">{briefData.submission.project_name}</p>
                          </div>
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div>
                              <h6 className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-2">Problem Statement</h6>
                              <p className="text-slate-300 text-sm leading-relaxed">{briefData.submission.problem_statement}</p>
                            </div>
                            <div>
                              <h6 className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-2">Solution Description</h6>
                              <p className="text-slate-300 text-sm leading-relaxed">{briefData.submission.solution_description}</p>
                            </div>
                          </div>
                          <div>
                            <h6 className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-2">Tech Stack</h6>
                            <div className="flex flex-wrap gap-2">
                              {briefData.submission.tech_stack?.split(',').map((tech, i) => (
                                <span key={i} className="px-2.5 py-1 bg-slate-800 text-slate-300 border border-slate-700 rounded-md text-xs font-medium">
                                  {tech.trim()}
                                </span>
                              ))}
                            </div>
                          </div>
                          {briefData.submission.github_url && (
                            <div>
                              <h6 className="text-slate-400 text-xs uppercase tracking-wider font-semibold mb-2">Repository</h6>
                              <a href={briefData.submission.github_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>
                                {briefData.submission.github_url}
                              </a>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-slate-400 text-sm">No submission data available.</div>
                      )}
                    </div>

                    {/* SECTION 2: AI EVALUATION BRIEF */}
                    <div>
                      <div className="flex items-center gap-2 mb-6">
                        <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center text-indigo-400">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 2a10 10 0 1 0 10 10H12V2z" />
                            <path d="m12 12 9.9 4.9" />
                            <path d="M12 12 2.1 7.1" />
                          </svg>
                        </div>
                        <h5 className="text-white font-medium">AI Evaluation Brief</h5>
                      </div>
                      
                      {briefLoading ? (
                        <div className="flex items-center justify-center py-10">
                          <div className="text-indigo-400 text-sm font-medium animate-pulse flex items-center gap-2">
                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                              <circle cx="12" cy="12" r="10" strokeWidth="3" strokeOpacity="0.25" />
                              <path d="M12 2a10 10 0 0 1 10 10" strokeWidth="3" strokeLinecap="round" />
                            </svg>
                            Analyzing project submission...
                          </div>
                        </div>
                      ) : briefData ? (
                        <div className="space-y-6">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="bg-indigo-950/20 p-4 rounded-xl border border-indigo-500/20">
                              <h6 className="text-indigo-400 text-xs uppercase tracking-wider font-semibold mb-2">Problem Summary</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.problem_summary}</p>
                            </div>
                            <div className="bg-indigo-950/20 p-4 rounded-xl border border-indigo-500/20">
                              <h6 className="text-indigo-400 text-xs uppercase tracking-wider font-semibold mb-2">Solution Summary</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.solution_summary}</p>
                            </div>
                          </div>

                          <div className="bg-indigo-950/20 p-4 rounded-xl border border-indigo-500/20 border-l-2 border-l-indigo-500">
                            <h6 className="text-indigo-400 text-xs uppercase tracking-wider font-semibold mb-2">Technology Stack Analysis</h6>
                            <p className="text-slate-200 text-sm leading-relaxed">{briefData.technology_stack_analysis}</p>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="bg-emerald-950/20 p-4 rounded-xl border border-emerald-500/20 border-l-2 border-l-emerald-500">
                              <h6 className="text-emerald-400 text-xs uppercase tracking-wider font-semibold mb-2">Innovation Highlights</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.innovation_highlights}</p>
                            </div>
                            <div className="bg-blue-950/20 p-4 rounded-xl border border-blue-500/20 border-l-2 border-l-blue-500">
                              <h6 className="text-blue-400 text-xs uppercase tracking-wider font-semibold mb-2">Technical Complexity</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.technical_complexity_assessment}</p>
                            </div>
                            <div className="bg-cyan-950/20 p-4 rounded-xl border border-cyan-500/20 border-l-2 border-l-cyan-500">
                              <h6 className="text-cyan-400 text-xs uppercase tracking-wider font-semibold mb-2">Architecture Assessment</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.architecture_assessment}</p>
                            </div>
                            <div className="bg-amber-950/20 p-4 rounded-xl border border-amber-500/20 border-l-2 border-l-amber-500">
                              <h6 className="text-amber-400 text-xs uppercase tracking-wider font-semibold mb-2">Scalability Notes</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.scalability_assessment}</p>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div className="bg-rose-950/20 p-4 rounded-xl border border-rose-500/20 border-l-2 border-l-rose-500">
                              <h6 className="text-rose-400 text-xs uppercase tracking-wider font-semibold mb-2">Potential Risks</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.potential_risks}</p>
                            </div>
                            <div className="bg-fuchsia-950/20 p-4 rounded-xl border border-fuchsia-500/20 border-l-2 border-l-fuchsia-500">
                              <h6 className="text-fuchsia-400 text-xs uppercase tracking-wider font-semibold mb-2">Suggested Focus For Judges</h6>
                              <p className="text-slate-200 text-sm leading-relaxed">{briefData.suggested_areas_of_focus}</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-rose-400 text-sm py-4">Failed to load AI brief.</div>
                      )}
                    </div>

                    {/* SECTION 3: SCORING RUBRIC */}
                    {briefData && (
                      <div>
                        <div className="flex items-center gap-2 mb-6 pt-6 border-t border-slate-700/50">
                          <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center text-amber-400">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                            </svg>
                          </div>
                          <h5 className="text-white font-medium">Scoring Rubric</h5>
                        </div>

                        <div className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-6">
                          {scoreSuccess ? (
                            <div className="flex flex-col items-center justify-center py-8">
                              <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-500 mb-4">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                              </div>
                              <h4 className="text-emerald-400 font-medium text-lg">Score Submitted Successfully</h4>
                              <p className="text-slate-400 text-sm mt-2">Returning to pending evaluations...</p>
                            </div>
                          ) : (
                            <>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                                {["innovation", "technical_depth", "presentation", "feasibility", "impact"].map((criteria) => (
                                  <div key={criteria}>
                                    <div className="flex justify-between items-center mb-2">
                                      <label className="text-slate-300 text-sm font-medium capitalize">
                                        {criteria.replace('_', ' ')}
                                      </label>
                                      <span className="text-indigo-400 font-semibold">{scoringData[criteria].toFixed(1)} / 10</span>
                                    </div>
                                    <input 
                                      type="range" 
                                      min="1" 
                                      max="10" 
                                      step="0.5"
                                      value={scoringData[criteria]}
                                      onChange={(e) => handleScoreChange(criteria, e.target.value)}
                                      className="w-full accent-indigo-500"
                                      disabled={submittingScore}
                                    />
                                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                                      <span>Poor</span>
                                      <span>Excellent</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                              {scoreError && (
                                <div className="mt-6 px-4 py-2 rounded-lg bg-rose-500/10 text-rose-300 text-sm">
                                  {scoreError}
                                </div>
                              )}
                              <div className="pt-8 flex justify-end">
                                <button 
                                  onClick={() => handleSubmitScore(team.id)}
                                  disabled={submittingScore}
                                  className="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2 disabled:opacity-50"
                                >
                                  {submittingScore ? "Submitting..." : "Submit Score"}
                                  {!submittingScore && (
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                      <line x1="5" y1="12" x2="19" y2="12" />
                                      <polyline points="12 5 19 12 12 19" />
                                    </svg>
                                  )}
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
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
