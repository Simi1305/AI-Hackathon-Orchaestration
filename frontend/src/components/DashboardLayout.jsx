import { useState } from "react";
import { logout, getUsername } from "../api";

export default function DashboardLayout({ navItems, pageContent, active, setActive, role, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const username = getUsername() || "User";
  const initials = username.slice(0, 2).toUpperCase();

  const page = pageContent[active] || { title: "Dashboard", description: "" };

  const roleTitles = {
    ORGANIZER: "Event Organizer",
    PARTICIPANT: "Participant",
    MENTOR: "Mentor",
    JUDGE: "Judge",
  };

  return (
    <div className="flex h-screen bg-slate-950 font-sans overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ═══════════ SIDEBAR ═══════════ */}
      <aside
        className={`
        fixed lg:static inset-y-0 left-0 z-30
        flex flex-col w-64 bg-slate-900 border-r border-slate-800
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
      `}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-800">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-indigo-500 shadow-lg shadow-indigo-500/30 flex-shrink-0">
            <svg
              width="18"
              height="18"
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
          <div>
            <p className="text-white font-semibold text-[15px] tracking-tight leading-none">
              EventFlow
            </p>
            <p className="text-slate-500 text-[11px] mt-0.5 font-medium tracking-wide uppercase">
              Hackathon OS
            </p>
          </div>
        </div>

        <p className="px-5 pt-5 pb-2 text-[10.5px] font-semibold text-slate-500 tracking-widest uppercase">
          Main Menu
        </p>

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = active === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActive(item.id);
                  setSidebarOpen(false);
                }}
                className={`
                  group w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left
                  transition-all duration-200 ease-in-out cursor-pointer
                  ${isActive ? "bg-indigo-500/15 text-indigo-400" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"}
                `}
              >
                <span
                  className={`flex-shrink-0 transition-colors duration-200 ${isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"}`}
                >
                  {item.icon}
                </span>
                <span className="flex-1 text-[13.5px] font-medium">
                  {item.label}
                </span>
                {item.badge && (
                  <span
                    className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md tabular-nums ${
                      item.badgeAlert
                        ? "bg-rose-500/20 text-rose-400"
                        : isActive
                          ? "bg-indigo-500/25 text-indigo-300"
                          : "bg-slate-800 text-slate-500 group-hover:bg-slate-700 group-hover:text-slate-400"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User card */}
        <div className="p-3 mt-auto border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-slate-800 transition-colors duration-200 cursor-pointer group">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-md">
              <span className="text-white text-[11px] font-bold">{initials}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-slate-200 text-[12.5px] font-medium truncate leading-none">
                {username}
              </p>
              <p className="text-slate-500 text-[11px] mt-0.5 truncate">
                {roleTitles[role] || role}
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); logout(); }}
              className="text-slate-600 hover:text-rose-400 transition-colors"
              title="Logout"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ═══════════ MAIN CONTENT ═══════════ */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* ── Top navbar ── */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950 flex-shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-slate-400 hover:text-white transition-colors"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <div>
              <h1 className="text-white font-semibold text-[17px] leading-tight">
                {page.title}
              </h1>
              <p className="text-slate-500 text-[12px] mt-0.5 hidden sm:block">
                {page.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/50 text-slate-400 hover:text-slate-200 px-3 py-2 rounded-lg text-[12.5px] transition-all duration-200 hidden sm:flex">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              Search...
              <span className="ml-1 text-[10px] bg-slate-700 px-1.5 py-0.5 rounded-md font-mono text-slate-500">
                ⌘K
              </span>
            </button>
            <button className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all duration-200">
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-rose-500 rounded-full ring-1 ring-slate-950" />
            </button>
            <button className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all duration-200">
              <svg
                width="17"
                height="17"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>
        </header>

        {/* ── Page body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-4 bg-slate-950">
          {children}
        </div>
      </main>
    </div>
  );
}
