import { useState, useEffect } from "react";
import { fetchWithAuth, postWithAuth } from "../api";

/* ─────────────────────────────────────────────────────────
   PENDING APPROVALS DATA
   These represent AI-generated actions awaiting human sign-off.
───────────────────────────────────────────────────────────*/
const initialApprovals = [
  {
    id: "team-formation",
    title: "Team Formation Review",
    description:
      "AI-generated teams are awaiting organizer approval before participants are notified.",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
    meta: "AI-balanced by skill, experience & institution",
    accentBg: "bg-indigo-500/10",
    accentIcon: "bg-indigo-500/15 text-indigo-400",
    accentBorder: "border-indigo-500/20",
  },
  {
    id: "mentor-assignment",
    title: "Mentor Assignment Review",
    description:
      "AI assigned mentors based on each team's detected skill gaps and mentor expertise.",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="8" r="4" />
        <path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
        <path d="M16 3.5l2 2-3.5 3.5" />
      </svg>
    ),
    meta: "Mentors matched to teams by expertise",
    accentBg: "bg-violet-500/10",
    accentIcon: "bg-violet-500/15 text-violet-400",
    accentBorder: "border-violet-500/20",
  },
  {
    id: "score-anomaly",
    title: "Score Anomaly Review",
    description:
      "Unusual scoring deviations detected across 3 judge submissions. Flagged for human review.",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    meta: "Flagged by the anomaly detection engine",
    accentBg: "bg-amber-500/10",
    accentIcon: "bg-amber-500/15 text-amber-400",
    accentBorder: "border-amber-500/20",
  },
  {
    id: "leaderboard-publish",
    title: "Leaderboard Publication Approval",
    description:
      "Final rankings have been computed and are ready to be published to all participants.",
    icon: (
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    meta: "Final rankings ready to publish",
    accentBg: "bg-emerald-500/10",
    accentIcon: "bg-emerald-500/15 text-emerald-400",
    accentBorder: "border-emerald-500/20",
  },
];

/* ── Single approval card ── */
export function ApprovalCard({ item, status, onApprove, onReject }) {
  const isPending = status === "pending";
  const isApproved = status === "approved";
  const isRejected = status === "rejected";

  return (
    <div
      className={`
      group relative bg-slate-900 border rounded-2xl p-5
      transition-all duration-200 ease-in-out
      ${isPending ? "border-slate-800 hover:border-slate-700" : ""}
      ${isApproved ? "border-emerald-500/30 bg-emerald-500/5" : ""}
      ${isRejected ? "border-rose-500/25 bg-rose-500/5" : ""}
    `}
    >
      {/* Top row: icon + status badge */}
      <div className="flex items-start justify-between mb-2">
        {/* Icon */}
        <div
          className={`flex items-center justify-center w-9 h-9 rounded-xl flex-shrink-0 ${item.accentIcon}`}
        >
          {item.icon}
        </div>

        {/* Status badge */}
        {isPending && (
          <span className="flex items-center gap-1.5 text-[10.5px] font-semibold px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-400">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-60" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500" />
            </span>
            Pending
          </span>
        )}
        {isApproved && (
          <span className="flex items-center gap-1.5 text-[10.5px] font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Approved
          </span>
        )}
        {isRejected && (
          <span className="flex items-center gap-1.5 text-[10.5px] font-semibold px-2.5 py-1 rounded-full bg-rose-500/15 border border-rose-500/25 text-rose-400">
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Rejected
          </span>
        )}
      </div>

      {/* Title */}
      <h4 className="text-white font-semibold text-[13.5px] leading-snug mb-1">
        {item.title}
      </h4>

      {/* Description */}
      <p className="text-slate-500 text-[12px] leading-relaxed mb-3">
        {item.description}
      </p>

      {/* Meta chip */}
      <div
        className={`inline-flex items-center gap-1.5 text-[10.5px] font-medium px-2.5 py-1 rounded-lg border mb-4 ${item.accentBg} ${item.accentBorder} text-slate-400`}
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        {item.meta}
      </div>

      {/* Action buttons — only shown while pending */}
      {isPending && (
        <div className="flex items-center gap-2">
          <button
            onClick={onApprove}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[12px] font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/25 hover:border-emerald-500/40 text-emerald-400 hover:text-emerald-300 transition-all duration-200"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Approve
          </button>
          <button
            onClick={onReject}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[12px] font-semibold bg-slate-800 hover:bg-rose-500/15 border border-slate-700 hover:border-rose-500/30 text-slate-400 hover:text-rose-400 transition-all duration-200"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Reject
          </button>
        </div>
      )}

      {/* Resolved message */}
      {!isPending && (
        <p
          className={`text-[11.5px] font-medium ${isApproved ? "text-emerald-500/70" : "text-rose-500/70"}`}
        >
          {isApproved
            ? "Action has been approved and queued for execution."
            : "Action has been rejected and dismissed."}
        </p>
      )}
    </div>
  );
}

/* ── Type -> display metadata (icons, copy, accents) ── */
const ICONS = {
  team: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  mentor: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" /><path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" /><path d="M16 3.5l2 2-3.5 3.5" />
    </svg>
  ),
  alert: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  trophy: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  mail: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16v12H5.17L4 17.17V4z" /><path d="M8 9h8M8 12h5" />
    </svg>
  ),
  arrow: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" />
    </svg>
  ),
};

const TYPE_META = {
  TEAM_REVIEW: {
    title: "Team Formation Review",
    description: "AI-generated teams are awaiting organizer approval before participants are notified.",
    meta: "AI-balanced by skill, experience & institution",
    accentBg: "bg-indigo-500/10", accentIcon: "bg-indigo-500/15 text-indigo-400", accentBorder: "border-indigo-500/20",
    icon: ICONS.team,
  },
  MENTOR_ASSIGNMENT_REVIEW: {
    title: "Mentor Assignment Review",
    description: "AI matched mentors to teams based on each team's skill gaps and mentor expertise.",
    meta: "Mentors matched by expertise",
    accentBg: "bg-violet-500/10", accentIcon: "bg-violet-500/15 text-violet-400", accentBorder: "border-violet-500/20",
    icon: ICONS.mentor,
  },
  ANOMALY_REVIEW: {
    title: "Score Anomaly Review",
    description: "Unusual scoring deviations were detected and flagged for human review.",
    meta: "Flagged by the anomaly detection engine",
    accentBg: "bg-amber-500/10", accentIcon: "bg-amber-500/15 text-amber-400", accentBorder: "border-amber-500/20",
    icon: ICONS.alert,
  },
  RESULT_PUBLICATION_REVIEW: {
    title: "Leaderboard Publication Approval",
    description: "Final rankings have been computed and are ready to publish to all participants.",
    meta: "Final rankings ready to publish",
    accentBg: "bg-emerald-500/10", accentIcon: "bg-emerald-500/15 text-emerald-400", accentBorder: "border-emerald-500/20",
    icon: ICONS.trophy,
  },
  MESSAGE_SENDING_REVIEW: {
    title: "Communication Review",
    description: "A stage communication is drafted and awaiting approval before it is sent.",
    meta: "Awaiting send approval",
    accentBg: "bg-sky-500/10", accentIcon: "bg-sky-500/15 text-sky-400", accentBorder: "border-sky-500/20",
    icon: ICONS.mail,
  },
  PROGRESSION_INVITE_REVIEW: {
    title: "Progression Invite Review",
    description: "Qualifying teams are ready to receive their progression invitations.",
    meta: "Progression invites ready",
    accentBg: "bg-fuchsia-500/10", accentIcon: "bg-fuchsia-500/15 text-fuchsia-400", accentBorder: "border-fuchsia-500/20",
    icon: ICONS.arrow,
  },
};

const DEFAULT_META = {
  title: "Approval Required",
  description: "An AI-generated action is awaiting your review.",
  meta: "Awaiting review",
  accentBg: "bg-slate-500/10", accentIcon: "bg-slate-500/15 text-slate-400", accentBorder: "border-slate-500/20",
  icon: ICONS.alert,
};

/* ── Pending Approvals section (wired to live backend) ── */
export default function PendingApprovalsSection() {
  const [approvals, setApprovals] = useState([]);
  const [statuses, setStatuses] = useState({});
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await fetchWithAuth("/approvals/pending");
      if (data) setApprovals(data);
    } catch (e) {
      console.error("Failed to load pending approvals:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const approve = async (id) => {
    setStatuses((s) => ({ ...s, [id]: "approved" }));
    try {
      await postWithAuth(`/approvals/${id}/approve`, { resolved_by: "admin" });
    } catch (e) {
      console.error(e);
    }
    setTimeout(load, 900);
  };

  const reject = async (id) => {
    setStatuses((s) => ({ ...s, [id]: "rejected" }));
    try {
      await postWithAuth(`/approvals/${id}/reject`, {
        reason: "Rejected by organizer from the dashboard.",
        resolved_by: "admin",
      });
    } catch (e) {
      console.error(e);
    }
    setTimeout(load, 900);
  };

  const approveAllTeams = async () => {
    try { await postWithAuth("/api/v1/organizer/approvals/approve-team-formations", {}); }
    catch (e) { console.error(e); }
    setTimeout(load, 700);
  };

  const pendingCount = approvals.filter((a) => !statuses[a.id]).length;
  const teamReviewCount = approvals.filter((a) => a.approval_type === "TEAM_REVIEW" && !statuses[a.id]).length;

  return (
    <div className="mt-3">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2.5 mb-0.5">
            <h2 className="text-white font-semibold text-[15px]">Pending Approvals</h2>
            {pendingCount > 0 && (
              <span className="flex items-center gap-1 text-[10.5px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/25 text-amber-400">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-70" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500" />
                </span>
                {pendingCount} pending
              </span>
            )}
          </div>
          <p className="text-slate-500 text-[12px]">
            AI-generated actions awaiting organizer review &amp; approval
          </p>
        </div>
        {teamReviewCount > 1 && (
          <button onClick={approveAllTeams}
            className="px-3 py-2 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-[12px] font-semibold transition-colors">
            Approve all {teamReviewCount} team formations
          </button>
        )}
      </div>

      {/* Divider with AI label */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1 h-px bg-slate-800" />
        <span className="flex items-center gap-1.5 text-[10.5px] text-slate-500 font-medium">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          AI assists · Humans approve
        </span>
        <div className="flex-1 h-px bg-slate-800" />
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm py-8 text-center">Loading approvals...</div>
      ) : approvals.length === 0 ? (
        <div className="text-slate-500 text-sm py-8 text-center">
          No pending approvals — you're all caught up.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {approvals.map((a) => {
            const base = TYPE_META[a.approval_type] || DEFAULT_META;
            const item = {
              ...base,
              meta: a.team_id ? `${base.meta} · Team #${a.team_id}` : base.meta,
            };
            return (
              <ApprovalCard
                key={a.id}
                item={item}
                status={statuses[a.id] || "pending"}
                onApprove={() => approve(a.id)}
                onReject={() => reject(a.id)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
