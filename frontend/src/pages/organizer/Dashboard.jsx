import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import HeroCard from "../../components/HeroCard";
import LineChart from "../../components/LineChart";
import PendingApprovalsSection from "../../components/ApprovalCard";
import { fetchWithAuth, postWithAuth, putWithAuth, getRole } from "../../api";

import Teams from "./Teams";
import Participants from "./Participants";
import Approvals from "./Approvals";
/* ── Nav items ── */
const navItems = [
  {
    id: "dashboard",
    label: "Dashboard",
    badge: null,
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    id: "participants",
    label: "Participants",
    badge: "248",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="9" cy="7" r="3.5" />
        <path d="M2 20c0-4 3-6 7-6s7 2 7 6" />
        <path d="M16 3.5a3.5 3.5 0 0 1 0 7" />
        <path d="M22 20c0-3.5-2-5.5-6-6" />
      </svg>
    ),
  },
  {
    id: "teams",
    label: "Teams",
    badge: "36",
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: "approvals",
    label: "Approvals",
    badge: "5",
    badgeAlert: true,
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    id: "leaderboard",
    label: "Leaderboard",
    badge: null,
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
      </svg>
    ),
  },
  {
    id: "certificates",
    label: "Certificates",
    badge: null,
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
        <line x1="12" y1="22.08" x2="12" y2="12"></line>
      </svg>
    ),
  },
  {
    id: "comms",
    label: "Communications",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 4h16v12H5.17L4 17.17V4z" />
        <path d="M8 9h8M8 12h5" />
      </svg>
    ),
  },
  {
    id: "timeline",
    label: "Timeline",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    id: "settings",
    label: "Settings",
    badge: null,
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H2a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 3.6 8a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H8a1.65 1.65 0 0 0 1-1.51V2a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H22a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
];

const pageContent = {
  dashboard: {
    title: "Dashboard",
    description:
      "Overview of your hackathon event metrics and key performance indicators.",
  },
  participants: {
    title: "Participants",
    description:
      "Manage and track all registered participants across the event.",
  },
  teams: {
    title: "Teams",
    description:
      "Monitor team formation, composition, and current project status.",
  },
  approvals: {
    title: "Approvals",
    description: "Review and action pending requests requiring your attention.",
  },
  leaderboard: {
    title: "Leaderboard",
    description:
      "Live rankings based on judge scores, peer votes, and milestones.",
  },
  analytics: {
    title: "Analytics",
    description: "Deep-dive into event data, trends, and engagement insights.",
  },
  certificates: {
    title: "Certificates",
    description:
      "Generate and publish hackathon certificates for participants.",
  },
  comms: {
    title: "Communications",
    description:
      "Draft stage messages with AI, preview, send, and track delivery per recipient.",
  },
  timeline: {
    title: "Event Timeline",
    description:
      "Track the current event stage and a live log of system actions.",
  },
  settings: {
    title: "Event Settings",
    description:
      "Configure team distribution rules and scoring weights for the event.",
  },
};

const heroCards = [
  {
    id: "participants",
    title: "Total Participants",
    value: "248",
    change: "+18 today",
    up: true,
    footer: "Registered & verified",
    iconWrapCls: "bg-indigo-500/15",
    iconCls: "text-indigo-400",
    trendBg: "bg-indigo-500/10",
    trendText: "text-indigo-300",
    borderHover: "hover:border-indigo-500/40",
    dotColor: "#818cf8",
    spark: [48, 60, 55, 72, 68, 80, 85, 95],
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="9" cy="7" r="3.5" />
        <path d="M2 20c0-4 3-6 7-6s7 2 7 6" />
        <path d="M16 3.5a3.5 3.5 0 0 1 0 7" />
        <path d="M22 20c0-3.5-2-5.5-6-6" />
      </svg>
    ),
  },
  {
    id: "teams",
    title: "Teams Formed",
    value: "36",
    change: "+4 this week",
    up: true,
    footer: "Active competing teams",
    iconWrapCls: "bg-violet-500/15",
    iconCls: "text-violet-400",
    trendBg: "bg-violet-500/10",
    trendText: "text-violet-300",
    borderHover: "hover:border-violet-500/40",
    dotColor: "#a78bfa",
    spark: [18, 20, 22, 24, 26, 28, 32, 36],
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  {
    id: "approvals",
    title: "Pending Approvals",
    value: "5",
    change: "Needs review",
    up: false,
    footer: "Awaiting organizer action",
    alert: true,
    iconWrapCls: "bg-rose-500/15",
    iconCls: "text-rose-400",
    trendBg: "bg-rose-500/10",
    trendText: "text-rose-300",
    borderHover: "hover:border-rose-500/40",
    dotColor: "#fb7185",
    spark: [2, 4, 3, 6, 5, 7, 6, 5],
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
  },
  {
    id: "judges",
    title: "Active Judges",
    value: "14",
    change: "All online now",
    up: true,
    footer: "Currently evaluating",
    iconWrapCls: "bg-emerald-500/15",
    iconCls: "text-emerald-400",
    trendBg: "bg-emerald-500/10",
    trendText: "text-emerald-300",
    borderHover: "hover:border-emerald-500/40",
    dotColor: "#34d399",
    spark: [8, 9, 9, 10, 11, 12, 13, 14],
    icon: (
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 2a5 5 0 1 1 0 10A5 5 0 0 1 12 2z" />
        <path d="M6.5 22a5.5 5.5 0 0 1 11 0" />
        <path d="M17 8l2 2 3-4" />
      </svg>
    ),
  },
];

export default function OrganizerDashboard() {
  const [active, setActive] = useState("dashboard");
  const [dashboardData, setDashboardData] = useState(null);
  const [triggerLoading, setTriggerLoading] = useState(false);
  const [config, setConfig] = useState(null);
  const [savingConfig, setSavingConfig] = useState(false);
  const [configMsg, setConfigMsg] = useState("");
  const [activity, setActivity] = useState([]);
  const [advancing, setAdvancing] = useState(false);
  const [commType, setCommType] = useState("team_welcome");
  const [commSubject, setCommSubject] = useState("");
  const [commBody, setCommBody] = useState("");
  const [commDrafting, setCommDrafting] = useState(false);
  const [commSending, setCommSending] = useState(false);
  const [commLog, setCommLog] = useState([]);
  const [commMsg, setCommMsg] = useState("");
  const [certMsg, setCertMsg] = useState("");
  const [certList, setCertList] = useState([]);

  useEffect(() => {
    if (active === "settings" && !config) {
      fetchWithAuth("/api/v1/organizer/event-config")
        .then((c) => c && setConfig(c))
        .catch((e) => console.error("Failed to load event config:", e));
    }
  }, [active, config]);

  const updateConfigField = (field, value) =>
    setConfig((prev) => ({ ...prev, [field]: value }));

  const weightsSum = config
    ? ["weight_innovation","weight_technical_depth","weight_presentation","weight_feasibility","weight_impact"]
        .reduce((a, k) => a + Number(config[k] || 0), 0)
    : 0;

  const handleSaveConfig = async () => {
    setSavingConfig(true);
    setConfigMsg("");
    try {
      const payload = {
        event_name: config.event_name,
        team_size: Number(config.team_size),
        max_same_institution: Number(config.max_same_institution),
        required_skills: config.required_skills || "",
        weight_innovation: Number(config.weight_innovation),
        weight_technical_depth: Number(config.weight_technical_depth),
        weight_presentation: Number(config.weight_presentation),
        weight_feasibility: Number(config.weight_feasibility),
        weight_impact: Number(config.weight_impact),
        anomaly_threshold: Number(config.anomaly_threshold),
      };
      const updated = await putWithAuth("/api/v1/organizer/event-config", payload);
      if (updated) { setConfig(updated); setConfigMsg("Saved."); }
    } catch (e) {
      setConfigMsg("Failed to save. Check the values and try again.");
    } finally {
      setSavingConfig(false);
    }
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await fetchWithAuth("/api/v1/dashboard/full-analytics");
        if (data) setDashboardData(data);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      }
    }
    fetchData();
  }, [active]);

  useEffect(() => {
    if (active === "timeline") {
      if (!config) {
        fetchWithAuth("/api/v1/organizer/event-config").then((c) => c && setConfig(c)).catch(() => {});
      }
      fetchWithAuth("/api/v1/organizer/activity-log").then((a) => a && setActivity(a)).catch(() => {});
    }
  }, [active, config]);

  const STAGES = ["SETUP", "TEAM_FORMATION", "EVALUATION", "RESULTS", "COMPLETED"];
  const handleAdvanceStage = async () => {
    setAdvancing(true);
    try {
      const res = await postWithAuth("/api/v1/organizer/advance-stage", {});
      if (res) {
        setConfig((prev) => (prev ? { ...prev, current_stage: res.current_stage } : prev));
        const a = await fetchWithAuth("/api/v1/organizer/activity-log");
        if (a) setActivity(a);
      }
    } catch (e) {
      console.error("Advance stage failed:", e);
    } finally {
      setAdvancing(false);
    }
  };

  useEffect(() => {
    if (active === "comms") {
      fetchWithAuth("/api/v1/organizer/communications").then((l) => l && setCommLog(l)).catch(() => {});
    }
  }, [active]);

  const loadCerts = () =>
    fetchWithAuth("/api/v1/organizer/certificates").then((c) => c && setCertList(c)).catch(() => {});
  useEffect(() => {
    if (active === "certificates") loadCerts();
  }, [active]);

  const handleDraftComm = async () => {
    setCommDrafting(true);
    setCommMsg("");
    try {
      const d = await postWithAuth("/api/v1/organizer/communications/draft", { stage: commType });
      if (d) { setCommSubject(d.subject); setCommBody(d.body); }
    } catch (e) {
      setCommMsg("Could not draft. Try again.");
    } finally {
      setCommDrafting(false);
    }
  };

  const handleSendComm = async () => {
    if (!commSubject || !commBody) { setCommMsg("Draft or write a message first."); return; }
    setCommSending(true);
    setCommMsg("");
    try {
      const res = await postWithAuth("/api/v1/organizer/communications/send", {
        communication_type: commType, subject: commSubject, body: commBody,
      });
      if (res) {
        setCommMsg(res.message);
        const l = await fetchWithAuth("/api/v1/organizer/communications");
        if (l) setCommLog(l);
      }
    } catch (e) {
      setCommMsg("Send failed. Check the message and try again.");
    } finally {
      setCommSending(false);
    }
  };

  const handleTriggerFormation = async () => {
    setTriggerLoading(true);
    try {
      await postWithAuth("/api/v1/trigger-team-formation", {});
    } catch (err) {
      console.error("Team formation failed:", err);
    } finally {
      setTriggerLoading(false);
    }
  };

  const navItemsDynamic = navItems.map((item) => {
    if (!dashboardData) {
      return ["participants", "teams", "approvals"].includes(item.id)
        ? { ...item, badge: null }
        : item;
    }
    if (item.id === "participants") return { ...item, badge: String(dashboardData.total_participants) };
    if (item.id === "teams") return { ...item, badge: String(dashboardData.teams_formed) };
    if (item.id === "approvals") return { ...item, badge: dashboardData.pending_approvals ? String(dashboardData.pending_approvals) : null };
    return item;
  });

  const chartDateLabels = Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (13 - i));
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  });

  return (
    <DashboardLayout
      navItems={navItemsDynamic}
      pageContent={pageContent}
      active={active}
      setActive={setActive}
      role={getRole()}
    >
      {active === "dashboard" && (
        <>
          {/* Hero Stat Cards */}
          <section className="mb-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-60" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500" />
                </span>
                <p className="text-slate-400 text-[12px] font-medium">
                  Live event data
                </p>
              </div>
              <button className="flex items-center gap-1.5 text-[11.5px] text-slate-500 hover:text-slate-300 transition-colors">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                Refresh
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {dashboardData &&
                [
                  {
                    id: "participants",
                    title: "Total Participants",
                    value: dashboardData.total_participants.toString(),
                    change: "Active in event",
                    up: true,
                    footer: "Registered & verified",
                    iconWrapCls: "bg-indigo-500/15",
                    iconCls: "text-indigo-400",
                    trendBg: "bg-indigo-500/10",
                    trendText: "text-indigo-300",
                    borderHover: "hover:border-indigo-500/40",
                    dotColor: "#818cf8",
                    spark: dashboardData.participants_history,
                    icon: (
                      <svg
                        width="19"
                        height="19"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <circle cx="9" cy="7" r="3.5" />
                        <path d="M2 20c0-4 3-6 7-6s7 2 7 6" />
                        <path d="M16 3.5a3.5 3.5 0 0 1 0 7" />
                        <path d="M22 20c0-3.5-2-5.5-6-6" />
                      </svg>
                    ),
                  },
                  {
                    id: "teams",
                    title: "Teams Formed",
                    value: dashboardData.teams_formed.toString(),
                    change: "Competing teams",
                    up: true,
                    footer: "Active project teams",
                    iconWrapCls: "bg-violet-500/15",
                    iconCls: "text-violet-400",
                    trendBg: "bg-violet-500/10",
                    trendText: "text-violet-300",
                    borderHover: "hover:border-violet-500/40",
                    dotColor: "#a78bfa",
                    spark: dashboardData.engagement_history,
                    icon: (
                      <svg
                        width="19"
                        height="19"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                    ),
                  },
                  {
                    id: "approvals",
                    title: "Pending Approvals",
                    value: dashboardData.pending_approvals.toString(),
                    change: "Needs review",
                    up: false,
                    footer: "Awaiting organizer action",
                    alert: dashboardData.pending_approvals > 0,
                    iconWrapCls: "bg-rose-500/15",
                    iconCls: "text-rose-400",
                    trendBg: "bg-rose-500/10",
                    trendText: "text-rose-300",
                    borderHover: "hover:border-rose-500/40",
                    dotColor: "#fb7185",
                    spark: [
                      2,
                      4,
                      3,
                      6,
                      5,
                      7,
                      dashboardData.pending_approvals,
                      dashboardData.pending_approvals,
                    ],
                    icon: (
                      <svg
                        width="19"
                        height="19"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M9 11l3 3L22 4" />
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                      </svg>
                    ),
                  },
                  {
                    id: "judges",
                    title: "Active Judges",
                    value: dashboardData.active_judges.toString(),
                    change: "All online now",
                    up: true,
                    footer: "Currently evaluating",
                    iconWrapCls: "bg-emerald-500/15",
                    iconCls: "text-emerald-400",
                    trendBg: "bg-emerald-500/10",
                    trendText: "text-emerald-300",
                    borderHover: "hover:border-emerald-500/40",
                    dotColor: "#34d399",
                    spark: [
                      8,
                      9,
                      9,
                      10,
                      11,
                      12,
                      13,
                      dashboardData.active_judges,
                    ],
                    icon: (
                      <svg
                        width="19"
                        height="19"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M12 2a5 5 0 1 1 0 10A5 5 0 0 1 12 2z" />
                        <path d="M6.5 22a5.5 5.5 0 0 1 11 0" />
                        <path d="M17 8l2 2 3-4" />
                      </svg>
                    ),
                  },
                ].map((card) => <HeroCard key={card.id} card={card} />)}
            </div>
          </section>

          {/* Analytics Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-white font-semibold text-[14px]">
                    Event Analytics
                  </h2>
                  <span className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-semibold px-2 py-0.5 rounded-full">
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
                    </span>
                    Live Monitoring Active
                  </span>
                </div>
                <p className="text-slate-500 text-[12px]">
                  Participant growth, submissions &amp; engagement — last 14
                  days
                </p>
              </div>
              <div className="hidden sm:flex items-center gap-4 text-[11px] text-slate-500 mt-0.5 flex-shrink-0">
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full bg-indigo-400 inline-block" />
                  Participants
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full bg-violet-400 inline-block" />
                  Submissions
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 rounded-full bg-emerald-400 inline-block" />
                  Engagement
                </span>
              </div>
            </div>

            {dashboardData && (
              <LineChart
                participants={dashboardData.participants_history}
                submissions={dashboardData.submissions_history}
                engagement={dashboardData.engagement_history}
              />
            )}

            <div className="flex justify-between mt-1 px-1">
              {chartDateLabels.map((d, i) => (
                <span
                  key={i}
                  className={`text-[9px] text-slate-600 ${i % 2 !== 0 ? "hidden sm:inline" : ""}`}
                >
                  {d}
                </span>
              ))}
            </div>
          </div>

          {/* AI Insights */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            {dashboardData &&
              dashboardData.recent_insights.map((insight, idx) => {
                // Map types to classes
                let iconCls = "";
                let iconWrapCls = "";
                let textCls = "";
                let hoverCls = "";
                let icon = null;

                if (insight.type === "positive") {
                  iconCls = "text-indigo-400";
                  iconWrapCls = "bg-indigo-500/15";
                  textCls = "text-indigo-300";
                  hoverCls = "hover:border-indigo-500/30";
                  icon = (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                      <polyline points="17 6 23 6 23 12" />
                    </svg>
                  );
                } else if (insight.type === "neutral") {
                  iconCls = "text-violet-400";
                  iconWrapCls = "bg-violet-500/15";
                  textCls = "text-violet-300";
                  hoverCls = "hover:border-violet-500/30";
                  icon = (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                  );
                } else {
                  iconCls = "text-amber-400";
                  iconWrapCls = "bg-amber-500/15";
                  textCls = "text-amber-300";
                  hoverCls = "hover:border-amber-500/30";
                  icon = (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                  );
                }

                return (
                  <div
                    key={idx}
                    className={`flex items-center gap-3 p-3.5 rounded-xl bg-slate-900 border border-slate-800 transition-colors duration-200 ${hoverCls}`}
                  >
                    <div
                      className={`flex-shrink-0 w-8 h-8 rounded-lg ${iconWrapCls} ${iconCls} flex items-center justify-center`}
                    >
                      {icon}
                    </div>
                    <div className="min-w-0">
                      <p
                        className={`${textCls} text-[12.5px] font-semibold leading-tight`}
                      >
                        {insight.title}
                      </p>
                      <p className="text-slate-500 text-[11px] mt-0.5">
                        {insight.subtitle}
                      </p>
                    </div>
                  </div>
                );
              })}
          </div>

          {/* Team Formation Trigger */}
          <div className="mt-4 bg-slate-900 border border-slate-800 rounded-2xl p-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-semibold text-[14px]">
                  AI Team Formation
                </h3>
                <p className="text-slate-500 text-[12px] mt-1">
                  Trigger the AI engine to form balanced teams from registered
                  participants
                </p>
              </div>
              <button
                onClick={handleTriggerFormation}
                disabled={triggerLoading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[13px] font-semibold bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white transition-all duration-200 shadow-lg shadow-indigo-500/20 disabled:opacity-50"
              >
                {triggerLoading ? (
                  <>
                    <svg
                      className="animate-spin h-4 w-4"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        className="opacity-25"
                      />
                      <path
                        d="M4 12a8 8 0 0 1 8-8"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        className="opacity-75"
                      />
                    </svg>
                    Running...
                  </>
                ) : (
                  <>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Trigger Formation
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Pending Approvals */}
          <div className="mt-3">
            <PendingApprovalsSection />
          </div>
        </>
      )}

      {active === "leaderboard" && dashboardData && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 overflow-hidden">
          <h3 className="text-white font-semibold text-[15px] mb-4">
            Event Leaderboard
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[12px] uppercase tracking-wider">
                  <th className="pb-3 pl-2 font-medium">Rank</th>
                  <th className="pb-3 font-medium">Team Name</th>
                  <th className="pb-3 font-medium">Challenge</th>
                  <th className="pb-3 text-right pr-2 font-medium">
                    Final Score
                  </th>
                </tr>
              </thead>
              <tbody>
                {dashboardData.leaderboard.map((team, idx) => (
                  <tr
                    key={team.team_id}
                    className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors"
                  >
                    <td className="py-3 pl-2">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-bold ${
                          team.rank === 1
                            ? "bg-amber-500/20 text-amber-400"
                            : team.rank === 2
                              ? "bg-slate-300/20 text-slate-300"
                              : team.rank === 3
                                ? "bg-orange-600/20 text-orange-500"
                                : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        {team.rank}
                      </span>
                    </td>
                    <td className="py-3 text-[13px] font-semibold text-white">
                      {team.team_name}
                    </td>
                    <td className="py-3 text-[12px] text-slate-400">
                      {team.challenge}
                    </td>
                    <td className="py-3 pr-2 text-right text-[13px] font-mono text-indigo-300">
                      {team.final_score ? team.final_score.toFixed(2) : "N/A"}
                    </td>
                  </tr>
                ))}
                {dashboardData.leaderboard.length === 0 && (
                  <tr>
                    <td
                      colSpan="4"
                      className="py-8 text-center text-slate-500 text-[13px]"
                    >
                      No teams scored yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {active === "certificates" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-white font-semibold text-[15px]">
                Certificate Management
              </h3>
              <p className="text-slate-500 text-[13px] mt-1">
                Generate and distribute certificates for participants and
                mentors.
              </p>
            </div>
            <div className="p-3 rounded-xl bg-violet-500/15 text-violet-400">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
              </svg>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 border border-slate-800 rounded-xl bg-slate-800/20 flex flex-col items-center justify-center text-center">
              <h4 className="text-indigo-300 font-medium text-[14px] mb-2">
                Step 1: Generate Certificates
              </h4>
              <p className="text-slate-500 text-[12px] mb-5">
                Create personalized certificates for all participants in
                approved teams and active mentors.
              </p>
              <button
                onClick={async () => {
                  try {
                    const res = await postWithAuth(
                      "/api/v1/organizer/certificates/generate",
                      {},
                    );
                    setCertMsg(`Generated ${res.generated_count} certificates.`); loadCerts();
                  } catch (e) {
                    setCertMsg("Failed to generate certificates.");
                  }
                }}
                className="px-5 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-[13px] font-semibold transition-colors w-full"
              >
                Generate Certificates
              </button>
            </div>

            <div className="p-5 border border-slate-800 rounded-xl bg-slate-800/20 flex flex-col items-center justify-center text-center">
              <h4 className="text-emerald-400 font-medium text-[14px] mb-2">
                Step 2: Publish to Dashboards
              </h4>
              <p className="text-slate-500 text-[12px] mb-5">
                Make the generated certificates available for download in
                participant dashboards.
              </p>
              <button
                onClick={async () => {
                  try {
                    const res = await postWithAuth(
                      "/api/v1/organizer/certificates/publish",
                      {},
                    );
                    setCertMsg(`Published ${res.published_count} certificates.`); loadCerts();
                  } catch (e) {
                    setCertMsg("Failed to publish certificates.");
                  }
                }}
                className="px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-[13px] font-semibold transition-colors w-full"
              >
                Publish Certificates
              </button>
            </div>
          </div>

          {certMsg && (
            <div className="mt-5 px-4 py-2 rounded-lg bg-emerald-500/10 text-emerald-300 text-[13px]">
              {certMsg}
            </div>
          )}

          <div className="mt-6">
            <h4 className="text-slate-300 font-medium text-[13px] mb-3">
              Certificate types issued
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border border-slate-800 rounded-xl bg-slate-800/20">
                <span className="inline-block px-2 py-1 mb-2 rounded-md bg-indigo-500/10 text-indigo-300 text-[11px] font-semibold">
                  PARTICIPATION
                </span>
                <p className="text-slate-500 text-[12px]">
                  Issued to every participant on an approved team for taking part in the event.
                </p>
              </div>
              <div className="p-4 border border-slate-800 rounded-xl bg-slate-800/20">
                <span className="inline-block px-2 py-1 mb-2 rounded-md bg-amber-500/10 text-amber-300 text-[11px] font-semibold">
                  WINNER
                </span>
                <p className="text-slate-500 text-[12px]">
                  Awarded to members of top-ranked teams once results are approved and published.
                </p>
              </div>
              <div className="p-4 border border-slate-800 rounded-xl bg-slate-800/20">
                <span className="inline-block px-2 py-1 mb-2 rounded-md bg-emerald-500/10 text-emerald-300 text-[11px] font-semibold">
                  MENTOR
                </span>
                <p className="text-slate-500 text-[12px]">
                  Recognises mentors for the teams they guided through the hackathon.
                </p>
              </div>
            </div>
            <p className="text-slate-600 text-[11.5px] mt-4 leading-relaxed">
              Workflow: generate certificates first, review them, then publish to make them downloadable from each recipient's dashboard. Certificates are only created for approved teams and active mentors, so run this after results are finalised.
            </p>
          </div>

          {certList.length > 0 && (
            <div className="mt-6">
              <h4 className="text-slate-300 font-medium text-[13px] mb-3">
                Generated certificates ({certList.length})
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-slate-500 text-[11px] uppercase border-b border-slate-800">
                      <th className="py-2 pr-4">Recipient</th>
                      <th className="py-2 pr-4">Type</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {certList.map((c) => (
                      <tr key={c.id} className="border-b border-slate-800/60 text-[12px]">
                        <td className="py-2 pr-4 text-slate-300">{c.recipient}</td>
                        <td className="py-2 pr-4 text-slate-400">{c.certificate_type}</td>
                        <td className="py-2">
                          {c.is_published ? (
                            <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 text-[10px] font-semibold">Published</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 text-[10px] font-semibold">Draft - not yet published</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {active === "comms" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-white font-semibold text-[15px] mb-1">Compose a stage message</h3>
            <p className="text-slate-500 text-[13px] mb-5">Pick a stage, let AI draft it, edit if needed, then send.</p>

            <div className="flex gap-2 mb-5">
              <button onClick={() => setCommType("team_welcome")}
                className={commType === "team_welcome"
                  ? "px-4 py-2 rounded-lg bg-indigo-500 text-white text-[13px] font-semibold"
                  : "px-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-300 text-[13px]"}>
                Team assignment welcome
              </button>
              <button onClick={() => setCommType("eval_reminder")}
                className={commType === "eval_reminder"
                  ? "px-4 py-2 rounded-lg bg-indigo-500 text-white text-[13px] font-semibold"
                  : "px-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-300 text-[13px]"}>
                Evaluation reminder
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-slate-400 text-[12px]">Subject</span>
                <input type="text" value={commSubject} onChange={(e) => setCommSubject(e.target.value)}
                  placeholder="Draft with AI or type your own"
                  className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
              </div>
              <div>
                <span className="text-slate-400 text-[12px]">Message body (preview)</span>
                <textarea value={commBody} onChange={(e) => setCommBody(e.target.value)} rows={8}
                  placeholder="Draft with AI or type your own"
                  className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500 resize-y" />
              </div>
            </div>

            <div className="flex items-center gap-3 mt-5">
              <button onClick={handleDraftComm} disabled={commDrafting}
                className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-[13px] font-semibold transition-colors disabled:opacity-50">
                {commDrafting ? "Drafting..." : "Draft with AI"}
              </button>
              <button onClick={handleSendComm} disabled={commSending}
                className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-[13px] font-semibold transition-colors disabled:opacity-50">
                {commSending ? "Sending..." : "Send to recipients"}
              </button>
              {commMsg && <span className="text-[12px] text-slate-400">{commMsg}</span>}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-white font-semibold text-[15px] mb-4">Delivery log</h3>
            {commLog.length === 0 ? (
              <div className="text-slate-400 text-sm py-6">No messages sent yet.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-slate-500 text-[11px] uppercase">
                      <th className="py-2 pr-4">Recipient</th>
                      <th className="py-2 pr-4">Type</th>
                      <th className="py-2 pr-4">Subject</th>
                      <th className="py-2 pr-4">Status</th>
                      <th className="py-2">Sent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commLog.map((c) => (
                      <tr key={c.id} className="border-t border-slate-800 text-[12px]">
                        <td className="py-2 pr-4 text-slate-300">{c.recipient_name}<div className="text-slate-600 text-[11px]">{c.recipient_email}</div></td>
                        <td className="py-2 pr-4 text-slate-400">{c.communication_type}</td>
                        <td className="py-2 pr-4 text-slate-400 max-w-xs truncate">{c.subject}</td>
                        <td className="py-2 pr-4"><span className="px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-300 text-[10px] font-semibold">{c.status}</span></td>
                        <td className="py-2 text-slate-500 text-[11px]">{c.sent_at ? new Date(c.sent_at).toLocaleString() : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {active === "timeline" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-white font-semibold text-[15px]">Event Pipeline</h3>
                <p className="text-slate-500 text-[13px] mt-1">The fixed sequence of stages for this event.</p>
              </div>
              <button onClick={handleAdvanceStage} disabled={advancing || (config && config.current_stage === "COMPLETED")}
                className="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-[13px] font-semibold transition-colors disabled:opacity-50">
                {advancing ? "Advancing..." : "Advance stage"}
              </button>
            </div>
            <div className="flex items-center">
              {STAGES.map((stage, i) => {
                const curIdx = config ? STAGES.indexOf(config.current_stage) : 0;
                const done = i < curIdx;
                const isCurrent = i === curIdx;
                const dotCls = isCurrent
                  ? "bg-indigo-500 border-indigo-400 text-white"
                  : done
                  ? "bg-emerald-500/20 border-emerald-500 text-emerald-300"
                  : "bg-slate-800 border-slate-700 text-slate-500";
                return (
                  <div key={stage} className="flex items-center flex-1 last:flex-none">
                    <div className="flex flex-col items-center">
                      <div className={"w-9 h-9 rounded-full border flex items-center justify-center text-[12px] font-semibold " + dotCls}>
                        {i + 1}
                      </div>
                      <span className={"mt-2 text-[11px] " + (isCurrent ? "text-white" : "text-slate-500")}>
                        {stage.replace("_", " ")}
                      </span>
                    </div>
                    {i < STAGES.length - 1 && (
                      <div className={"h-0.5 flex-1 mx-2 " + (i < curIdx ? "bg-emerald-500/50" : "bg-slate-700")} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h3 className="text-white font-semibold text-[15px] mb-4">Activity Log</h3>
            {activity.length === 0 ? (
              <div className="text-slate-400 text-sm py-6">No activity recorded yet.</div>
            ) : (
              <div className="space-y-3">
                {activity.map((a, idx) => {
                  const isAnomaly = /anomal/i.test(a.message);
                  const color = isAnomaly ? "text-rose-300 bg-rose-500/15"
                    : a.category === "APPROVAL" ? "text-amber-300 bg-amber-500/10"
                    : a.category === "SCORE" ? "text-violet-300 bg-violet-500/10"
                    : a.category === "TEAM" ? "text-emerald-300 bg-emerald-500/10"
                    : "text-slate-300 bg-slate-700/40";
                  return (
                    <div key={idx} className={"flex items-start gap-3 pb-3 border-b border-slate-800 last:border-0 " + (isAnomaly ? "rounded-lg bg-rose-500/5 px-2 -mx-2" : "")}>
                      <span className={"px-2 py-1 rounded-md text-[10px] font-semibold " + color}>{isAnomaly ? "ANOMALY" : a.category}</span>
                      <div className="flex-1">
                        <p className={"text-[13px] " + (isAnomaly ? "text-rose-200 font-medium" : "text-slate-300")}>{a.message}</p>
                        <p className="text-slate-600 text-[11px] mt-0.5">{new Date(a.timestamp).toLocaleString()}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {active === "settings" && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="mb-6">
            <h3 className="text-white font-semibold text-[15px]">Event Settings</h3>
            <p className="text-slate-500 text-[13px] mt-1">
              These rules drive team formation and score consolidation. Changes apply to the next run.
            </p>
          </div>

          {!config ? (
            <div className="text-slate-400 text-sm py-8">Loading configuration...</div>
          ) : (
            <div className="space-y-8">
              <div>
                <h4 className="text-slate-300 font-medium text-[13px] mb-4">Team distribution rules</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="block">
                    <span className="text-slate-400 text-[12px]">Event name</span>
                    <input type="text" value={config.event_name || ""} onChange={(e) => updateConfigField("event_name", e.target.value)}
                      className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                  </label>
                  <label className="block">
                    <span className="text-slate-400 text-[12px]">Required skills (comma-separated)</span>
                    <input type="text" value={config.required_skills || ""} onChange={(e) => updateConfigField("required_skills", e.target.value)}
                      placeholder="e.g. ML, Backend, Frontend"
                      className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                  </label>
                  <label className="block">
                    <span className="text-slate-400 text-[12px]">Team size</span>
                    <input type="number" min="2" max="10" value={config.team_size} onChange={(e) => updateConfigField("team_size", e.target.value)}
                      className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                  </label>
                  <label className="block">
                    <span className="text-slate-400 text-[12px]">Max participants per institution per team</span>
                    <input type="number" min="1" max="10" value={config.max_same_institution} onChange={(e) => updateConfigField("max_same_institution", e.target.value)}
                      className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                  </label>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-slate-300 font-medium text-[13px]">Scoring weights</h4>
                  <span className={weightsSum.toFixed(2) === "1.00" ? "text-[12px] text-emerald-400" : "text-[12px] text-amber-400"}>
                    Sum: {weightsSum.toFixed(2)}{weightsSum.toFixed(2) === "1.00" ? "" : " (auto-normalised at scoring time)"}
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {[
                    ["weight_innovation", "Innovation"],
                    ["weight_technical_depth", "Technical depth"],
                    ["weight_presentation", "Presentation"],
                    ["weight_feasibility", "Feasibility"],
                    ["weight_impact", "Impact"],
                  ].map(([key, label]) => (
                    <label key={key} className="block">
                      <span className="text-slate-400 text-[12px]">{label}</span>
                      <input type="number" step="0.05" min="0" max="1" value={config[key]} onChange={(e) => updateConfigField(key, e.target.value)}
                        className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-slate-300 font-medium text-[13px] mb-4">Anomaly detection</h4>
                <label className="block max-w-xs">
                  <span className="text-slate-400 text-[12px]">Threshold (standard deviations)</span>
                  <input type="number" step="0.1" min="0.5" max="5" value={config.anomaly_threshold} onChange={(e) => updateConfigField("anomaly_threshold", e.target.value)}
                    className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-white text-[13px] focus:outline-none focus:border-indigo-500" />
                </label>
              </div>

              <div className="flex items-center gap-4 pt-2">
                <button onClick={handleSaveConfig} disabled={savingConfig}
                  className="px-5 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-[13px] font-semibold transition-colors disabled:opacity-50">
                  {savingConfig ? "Saving..." : "Save settings"}
                </button>
                {configMsg && <span className="text-[12px] text-slate-400">{configMsg}</span>}
              </div>
            </div>
          )}
        </div>
      )}

      {active === "participants" && <Participants />}
      {active === "teams" && <Teams />}
      {active === "approvals" && <PendingApprovalsSection />}
      {/* Placeholder for other nav pages */}
      {![
        "dashboard",
        "leaderboard",
        "certificates",
        "teams",
        "approvals",
        "participants",
        "settings",
        "timeline",
        "comms",
      ].includes(active) && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/15 text-indigo-400 flex items-center justify-center mb-4">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" />
            </svg>
          </div>
          <h2 className="text-white font-semibold text-lg mb-1">
            {pageContent[active]?.title}
          </h2>
          <p className="text-slate-500 text-[13px]">
            {pageContent[active]?.description}
          </p>
          <p className="text-slate-600 text-[12px] mt-4">
            Content coming soon...
          </p>
        </div>
      )}
    </DashboardLayout>
  );
}
