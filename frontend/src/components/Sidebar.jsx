import React from 'react';
import {
  Activity,
  Wallet,
  CreditCard,
  Target,
  PieChart,
  CalendarCheck,
  Sliders,
  MessageSquare,
  ShieldAlert,
  Clock
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, t }) {
  const navItems = [
    { id: 'overview', label: t.nav.overview, icon: Activity },
    { id: 'savings', label: t.nav.savings, icon: Wallet },
    { id: 'debt', label: t.nav.debt, icon: CreditCard },
    { id: 'goals', label: t.nav.goals, icon: Target },
    { id: 'allocation', label: t.nav.allocation, icon: PieChart },
    { id: 'retirement', label: t.nav.retirement, icon: Clock },
    { id: 'checklist', label: t.nav.checklist, icon: CalendarCheck },
    { id: 'whatif', label: t.nav.whatif, icon: Sliders },
    { id: 'chat', label: t.nav.chat, icon: MessageSquare, badge: 'AI Coach' },
  ];

  return (
    <aside className="w-full md:w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 p-3 flex md:flex-col gap-1 overflow-x-auto md:overflow-y-auto shrink-0 transition-colors">
      <div className="hidden md:block px-3 py-2 text-[11px] font-bold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
        Navigation
      </div>
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition whitespace-nowrap md:whitespace-normal text-left ${
              isActive
                ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400 dark:text-slate-500'}`} />
            <span className="flex-1">{item.label}</span>
            {item.badge && (
              <span className="hidden lg:inline text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 uppercase tracking-wider">
                {item.badge}
              </span>
            )}
          </button>
        );
      })}

      <div className="hidden md:block mt-auto pt-4 border-t border-slate-100 dark:border-slate-800">
        <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200/60 dark:border-slate-700/60">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            <span>Guaranteed Grounding</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
            All math computed by deterministic Python engine. No LLM hallucinations.
          </p>
        </div>
      </div>
    </aside>
  );
}
