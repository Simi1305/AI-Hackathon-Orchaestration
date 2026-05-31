import Sparkline from "./Sparkline";

export default function HeroCard({ card }) {
  return (
    <div
      className={`
      relative group overflow-hidden
      bg-slate-900 border border-slate-800 ${card.borderHover}
      rounded-2xl p-5
      transition-all duration-200 ease-in-out
      hover:bg-slate-900/90
    `}
    >
      {/* Top row: icon + sparkline or alert pulse */}
      <div className="flex items-start justify-between mb-4">
        {/* Icon chip */}
        <div
          className={`flex items-center justify-center w-10 h-10 rounded-xl flex-shrink-0 ${card.iconWrapCls} ${card.iconCls}`}
        >
          {card.icon}
        </div>

        {/* Right: alert pulse for urgent, sparkline otherwise */}
        {card.alert ? (
          <span className="relative flex h-2.5 w-2.5 mt-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-60" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
          </span>
        ) : (
          <div className="opacity-50 group-hover:opacity-90 transition-opacity duration-200 mt-0.5">
            <Sparkline data={card.spark} color={card.dotColor} />
          </div>
        )}
      </div>

      {/* Value */}
      <p className="text-white text-[28px] font-bold tracking-tight leading-none tabular-nums mb-1">
        {card.value}
      </p>

      {/* Title + footer */}
      <p className="text-slate-200 text-[13px] font-medium">{card.title}</p>
      <p className="text-slate-500 text-[11.5px] mt-0.5">{card.footer}</p>

      {/* Divider + trend badge + link */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-800">
        <span
          className={`
          inline-flex items-center gap-1.5
          text-[11px] font-semibold px-2 py-1 rounded-lg
          ${card.up ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"}
        `}
        >
          {/* Arrow */}
          <svg width="9" height="9" viewBox="0 0 9 9" fill="currentColor">
            {card.up ? (
              <path d="M4.5 1.5l3.5 6h-7z" />
            ) : (
              <path d="M4.5 7.5L1 1.5h7z" />
            )}
          </svg>
          {card.change}
        </span>
        <button className="text-[11px] text-slate-500 hover:text-indigo-400 font-medium transition-colors duration-150">
          View →
        </button>
      </div>
    </div>
  );
}
