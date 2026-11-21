import React, { useState } from 'react';
import { CalendarCheck, CheckCircle2, Circle, Clock, AlertTriangle, ShieldCheck, ArrowRight } from 'lucide-react';

export default function ActionPlanView({ actionPlan, t }) {
  const [items, setItems] = useState(actionPlan || []);

  const toggleComplete = (idx) => {
    setItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, completed: !item.completed } : item))
    );
  };

  if (!items || items.length === 0) return null;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CalendarCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Next 3-Month Priority Execution Checklist
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Strict Indian financial hierarchy: (1) Emergency Cushion → (2) High-Interest Debt → (3) Protection Buffer → (4) Milestone Goals → (5) Retirement. Timing is synced exclusively with monthly salary cashflow dates.
          </p>
        </div>

        <div className="px-3.5 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-bold text-emerald-700 dark:text-emerald-300 shrink-0">
          {items.filter((i) => i.completed).length} / {items.length} Actions Completed
        </div>
      </div>

      {/* Checklist items */}
      <div className="space-y-3">
        {items.map((item, idx) => {
          const isDone = item.completed;
          let badgeColor = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
          if (item.priority === 'Highest') badgeColor = 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300';
          else if (item.priority === 'High') badgeColor = 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300';
          else if (item.priority === 'Medium') badgeColor = 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300';
          else if (item.priority === 'Long-Term') badgeColor = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';

          return (
            <div
              key={idx}
              onClick={() => toggleComplete(idx)}
              className={`p-4 rounded-2xl border transition cursor-pointer flex items-start gap-4 ${
                isDone
                  ? 'bg-slate-50/70 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 opacity-60'
                  : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-emerald-400 dark:hover:border-emerald-600 shadow-sm'
              }`}
            >
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : (
                  <Circle className="w-5 h-5 text-slate-300 dark:text-slate-600 hover:text-emerald-500 transition" />
                )}
              </div>

              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Step {item.step} • {item.category}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${badgeColor}`}>
                    {item.priority}
                  </span>
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1 ml-auto">
                    <Clock className="w-3 h-3" />
                    <span>{item.timing}</span>
                  </span>
                </div>

                <h4 className={`text-sm font-bold text-slate-900 dark:text-white ${isDone ? 'line-through' : ''}`}>
                  {item.action}
                </h4>

                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  {item.reason}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
        <strong>Why no specific market timing?</strong> In personal finance, automated standing instructions (Day 1-5 post-salary) beat market timing attempts 100% of the time. We schedule your wealth building around your personal cashflow cycle, never market swings.
      </div>
    </div>
  );
}
