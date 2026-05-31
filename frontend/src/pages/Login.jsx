import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";

const quickLogins = [
  { label: "Organizer", username: "admin", color: "indigo", icon: "⚡" },
  { label: "Participant", username: "aarav", color: "violet", icon: "🎓" },
  { label: "Mentor", username: "mentor_sarah", color: "emerald", icon: "🧭" },
  { label: "Judge", username: "judge_michael", color: "amber", icon: "⚖️" },
];

const colorMap = {
  indigo: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/25 hover:border-indigo-500/50",
  violet: "bg-violet-500/15 text-violet-400 border-violet-500/30 hover:bg-violet-500/25 hover:border-violet-500/50",
  emerald: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25 hover:border-emerald-500/50",
  amber: "bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25 hover:border-amber-500/50",
};

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e?.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(username, password);
      const routes = { ORGANIZER: "/admin", PARTICIPANT: "/participant", MENTOR: "/mentor", JUDGE: "/judge" };
      navigate(routes[data.role] || "/admin");
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (user) => {
    setUsername(user);
    setPassword("password123");
    setTimeout(async () => {
      setError("");
      setLoading(true);
      try {
        const data = await login(user, "password123");
        const routes = { ORGANIZER: "/admin", PARTICIPANT: "/participant", MENTOR: "/mentor", JUDGE: "/judge" };
        navigate(routes[data.role] || "/admin");
      } catch (err) {
        setError("Quick login failed. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }, 100);
  };

  return (
    <div className="relative min-h-screen bg-slate-950 flex items-center justify-center px-4 overflow-hidden">
      {/* Floating gradient orbs */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 rounded-full blur-3xl" />

      {/* Login card */}
      <div className="relative w-full max-w-md z-10">
        {/* Logo section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500 shadow-lg shadow-indigo-500/30 mb-5">
            <svg
              width="26"
              height="26"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-500 to-indigo-600 bg-clip-text text-transparent mb-2">
            EventFlow
          </h1>
          <p className="text-slate-500 text-sm font-medium">
            AI-Powered Hackathon Orchestration Platform
          </p>
        </div>

        {/* Form card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl shadow-black/20">
          <div className="mb-6">
            <h2 className="text-white text-lg font-semibold">Welcome back</h2>
            <p className="text-slate-500 text-[13px] mt-1">Sign in to your account to continue</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            {/* Username */}
            <div>
              <label className="block text-slate-400 text-[12px] font-semibold uppercase tracking-wider mb-2">
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
                    <circle cx="12" cy="8" r="4" />
                    <path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white text-[13.5px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-200"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-slate-400 text-[12px] font-semibold uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white text-[13.5px] placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 transition-all duration-200"
                />
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 text-rose-400 text-[12.5px] font-medium bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-2.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full py-3 rounded-xl text-white font-semibold text-[14px] bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg shadow-indigo-500/20"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-25" />
                    <path d="M4 12a8 8 0 0 1 8-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
                  </svg>
                  Signing in...
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* Quick login */}
          <div className="mt-6 pt-6 border-t border-slate-800">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1 h-px bg-slate-800" />
              <span className="text-[10.5px] text-slate-500 font-medium uppercase tracking-wider">Quick Access</span>
              <div className="flex-1 h-px bg-slate-800" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              {quickLogins.map((q) => (
                <button
                  key={q.username}
                  onClick={() => handleQuickLogin(q.username)}
                  disabled={loading}
                  className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-[12px] font-semibold border transition-all duration-200 disabled:opacity-50 ${colorMap[q.color]}`}
                >
                  <span className="text-sm">{q.icon}</span>
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer text */}
        <p className="text-center text-slate-600 text-[11px] mt-6 font-medium">
          EventFlow Hackathon OS · AI-Orchestrated Event Platform
        </p>
      </div>
    </div>
  );
}
