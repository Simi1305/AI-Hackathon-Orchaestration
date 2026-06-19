import { useState, useEffect, useRef } from "react";
import { fetchWithAuth, postWithAuth } from "../../api";

function parseRosterCSV(text) {
  const lines = text.replace(/\r/g, "").split("\n").filter((l) => l.trim().length);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const col = (name) => headers.indexOf(name);
  const iName = col("name"), iEmail = col("email"), iInst = col("institution"),
        iSkills = col("skill_tags"), iExp = col("experience");
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const c = lines[i].split(",");
    const get = (j) => (j >= 0 && c[j] !== undefined ? c[j].trim() : "");
    let exp = get(iExp).toLowerCase();
    if (!["junior", "mid", "senior"].includes(exp)) exp = "mid";
    const skills = get(iSkills).replace(/;/g, ",") || "General";
    const name = get(iName), email = get(iEmail), institution = get(iInst);
    if (!name || !email || !institution) continue;
    rows.push({ name, email, institution, skill_tags: skills, experience: exp });
  }
  return rows;
}

export default function Participants() {
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const load = () =>
    fetchWithAuth("/participants/")
      .then((d) => d && setParticipants(d))
      .catch((e) => console.error("Failed to load participants:", e))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setMsg("");
    try {
      const text = await file.text();
      const rows = parseRosterCSV(text);
      if (rows.length === 0) {
        setMsg("Could not read any rows. Check the CSV headers: name, email, institution, skill_tags, experience.");
        return;
      }
      const res = await postWithAuth("/upload-roster/", { participants: rows });
      setMsg(res?.message || `Uploaded ${rows.length} participants.`);
      await load();
    } catch (err) {
      setMsg("Upload failed. Make sure the CSV columns are name, email, institution, skill_tags, experience.");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleForm = async () => {
    setBusy(true);
    setMsg("");
    try {
      const res = await postWithAuth("/api/v1/trigger-team-formation", {});
      setMsg(res?.teams_formed != null
        ? `Formed ${res.teams_formed} team(s). ${res.approvals_queued || 0} approval(s) queued for your review.`
        : "Team formation triggered.");
      await load();
    } catch (err) {
      setMsg("No unassigned participants to form teams from. Upload a roster first.");
    } finally {
      setBusy(false);
    }
  };

  const handleReform = async () => {
    setBusy(true); setMsg("");
    try {
      await postWithAuth("/api/v1/organizer/reform-teams", {});
      const res = await postWithAuth("/api/v1/trigger-team-formation", {});
      setMsg(res?.teams_formed != null
        ? `Re-formed ${res.teams_formed} team(s) from the current participants with the latest settings.`
        : "Teams re-formed.");
      await load();
    } catch (e) {
      setMsg("Could not re-form teams. Make sure participants are loaded.");
    } finally { setBusy(false); }
  };

  const handleReset = async () => {
    if (!window.confirm("Clear ALL event data (participants, teams, scores, approvals)? Accounts stay. Use this to start from your own roster.")) return;
    setBusy(true); setMsg("");
    try {
      await postWithAuth("/api/v1/organizer/reset-event", {});
      setMsg("Event cleared. Upload your roster to begin.");
      await load();
    } catch (e) {
      setMsg("Reset failed.");
    } finally { setBusy(false); }
  };

  const downloadSample = () => {
    const sample = [
      "name,email,institution,skill_tags,experience",
      "Diya Kapoor,diya.kapoor@demo.io,IIT Bombay,ML;Python,senior",
      "Kabir Anand,kabir.anand@demo.io,BITS Pilani,Backend;Node.js,mid",
      "Riya Nair,riya.nair@demo.io,NIT Trichy,Frontend;React,junior",
      "Arnav Joshi,arnav.joshi@demo.io,IIIT Hyderabad,DevOps;Docker,mid",
      "Sara Khan,sara.khan@demo.io,VIT Vellore,UI/UX;Figma,junior",
      "Veer Malhotra,veer.malhotra@demo.io,Delhi University,Cloud;AWS,senior",
    ].join("\n");
    const blob = new Blob([sample], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "sample_roster.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div>
          <h3 className="text-white font-semibold text-[15px]">Participant Roster</h3>
          <p className="text-slate-500 text-[13px] mt-1">
            Upload a roster, then form teams from the unassigned participants.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-300 text-[12px] font-semibold">
            {participants.length} participants
          </span>
          <button onClick={downloadSample}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[12px] font-medium transition-colors">
            Sample CSV
          </button>
          <button onClick={() => fileRef.current?.click()} disabled={busy}
            className="px-3 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-[12px] font-semibold transition-colors disabled:opacity-50">
            {busy ? "Working..." : "Upload roster (CSV)"}
          </button>
          <button onClick={handleForm} disabled={busy}
            className="px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-[12px] font-semibold transition-colors disabled:opacity-50">
            Form teams
          </button>
          <button onClick={handleReform} disabled={busy}
            className="px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-[12px] font-semibold transition-colors disabled:opacity-50">
            Re-form teams
          </button>
          <button onClick={handleReset} disabled={busy}
            className="px-3 py-2 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 text-[12px] font-semibold transition-colors disabled:opacity-50">
            Reset event
          </button>
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={handleFile} className="hidden" />
        </div>
      </div>

      {msg && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-slate-800/60 border border-slate-700 text-slate-300 text-[12.5px]">
          {msg}
        </div>
      )}

      {loading ? (
        <div className="text-slate-400 text-sm py-8 text-center">Loading roster...</div>
      ) : participants.length === 0 ? (
        <div className="text-slate-400 text-sm py-8 text-center">
          No participants yet. Click "Upload roster (CSV)" to load a list.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-slate-500 text-[11px] uppercase border-b border-slate-800">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Institution</th>
                <th className="py-2 pr-4">Skills</th>
                <th className="py-2 pr-4">Experience</th>
                <th className="py-2">Team</th>
              </tr>
            </thead>
            <tbody>
              {participants.map((p) => (
                <tr key={p.id} className="border-b border-slate-800/60 text-[13px]">
                  <td className="py-2.5 pr-4 text-white font-medium">
                    {p.name}
                    <div className="text-slate-600 text-[11px]">{p.email}</div>
                  </td>
                  <td className="py-2.5 pr-4 text-slate-400">{p.institution}</td>
                  <td className="py-2.5 pr-4">
                    <div className="flex flex-wrap gap-1">
                      {(p.skill_tags || "").split(",").filter(Boolean).map((s, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 text-[11px]">
                          {s.trim()}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 pr-4">
                    <span className="px-2 py-0.5 rounded-md bg-violet-500/10 text-violet-300 text-[11px] capitalize">
                      {p.experience}
                    </span>
                  </td>
                  <td className="py-2.5">
                    {p.team_id ? (
                      <span className="text-emerald-400 text-[12px]">Team #{p.team_id}</span>
                    ) : (
                      <span className="text-amber-400 text-[12px]">Unassigned</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
