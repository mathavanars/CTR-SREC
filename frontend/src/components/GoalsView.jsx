import React, { useState } from 'react';
import { Target, Calendar, TrendingUp, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, Clock, HelpCircle } from 'lucide-react';

export default function GoalsView({ goalsData, savingsCapacity, t }) {
  const [expandedGoal, setExpandedGoal] = useState(null);

  if (!goalsData) return null;

  const goals = goalsData.goals || [];

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Life Goals Feasibility Engine
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Each goal is mathematically inflation-adjusted (6% general, 8.5% education) and calculated using an annuity compounding formula against your available monthly surplus.
          </p>
        </div>

        <div className="flex items-center gap-4 border-t sm:border-t-0 sm:border-l border-slate-100 dark:border-slate-800 pt-3 sm:pt-0 sm:pl-6 shrink-0">
          <div>
            <span className="text-[11px] text-slate-400 font-medium block">Total Monthly SIP Needed</span>
            <span className="text-xl font-black text-slate-900 dark:text-white">
              ₹{goalsData.total_required_monthly_sip?.toLocaleString('en-IN')}/mo
            </span>
          </div>
          <div>
            <span className="text-[11px] text-slate-400 font-medium block">Feasibility Ratio</span>
            <span className="text-xl font-black text-emerald-600 dark:text-emerald-400">
              {goalsData.goals_on_track_ratio}%
            </span>
          </div>
        </div>
      </div>

      {/* Goal Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {goals.map((goal, idx) => {
          const isExpanded = expandedGoal === idx;
          const isSuccess = goal.feasibility === 'On Track';
          const isWarning = goal.feasibility === 'At Risk';

          let badgeCls = 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 border-rose-300 dark:border-rose-800';
          if (isSuccess) badgeCls = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
          if (isWarning) badgeCls = 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-300 dark:border-amber-800';

          return (
            <div
              key={goal.id || idx}
              className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between hover:border-slate-300 dark:hover:border-slate-700 transition"
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                      Priority: {goal.priority} • {goal.category}
                    </span>
                    <h4 className="font-bold text-slate-900 dark:text-white text-base mt-0.5">
                      {goal.name}
                    </h4>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border ${badgeCls}`}>
                    {goal.feasibility}
                  </span>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl mb-3 text-xs">
                  <div>
                    <span className="text-slate-400 text-[11px] block">Target (Today's Value)</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      ₹{goal.target_amount?.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block">Inflation-Adjusted (FV)</span>
                    <span className="font-bold text-slate-900 dark:text-white">
                      ₹{goal.future_target_amount?.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block">Target Date & Runway</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      {goal.target_date} ({goal.months_horizon} mos)
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px] block">Required Monthly SIP</span>
                    <span className="font-black text-emerald-600 dark:text-emerald-400 text-sm">
                      ₹{goal.required_monthly_sip?.toLocaleString('en-IN')}/mo
                    </span>
                  </div>
                </div>

                {/* Status Message */}
                <p className="text-xs text-slate-600 dark:text-slate-300 mb-3 flex items-start gap-1.5 leading-relaxed">
                  {isSuccess ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                  )}
                  <span>{goal.status_message}</span>
                </p>
              </div>

              {/* Suggested Fix Expander */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={() => setExpandedGoal(isExpanded ? null : idx)}
                  className="w-full flex items-center justify-between text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline py-1"
                >
                  <span>Suggested Optimization & Fix</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-2 p-3 bg-emerald-50/50 dark:bg-emerald-950/40 rounded-xl text-xs text-slate-700 dark:text-slate-300 border border-emerald-100 dark:border-emerald-900/40 space-y-1.5 leading-relaxed">
                    <p><strong>Actionable Fix:</strong> {goal.suggested_fix}</p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Assumptions applied: {goal.inflation_applied}% annual inflation, {goal.assumed_return}% CAGR based on {goal.years_horizon} year investment horizon.
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {goals.length === 0 && (
          <div className="md:col-span-2 p-8 text-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 text-slate-400 text-xs">
            No active financial goals recorded. Click "Edit Profile" to add goals like Buying a Home, Child Higher Education, or Emergency Cushions.
          </div>
        )}
      </div>
    </div>
  );
}
