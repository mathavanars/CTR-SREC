import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Wallet, Scissors, ShieldAlert, Sparkles, Building, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export default function SavingsView({ cashflow, emergency, t }) {
  if (!cashflow) return null;

  const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#64748b'];

  const breakdownData = cashflow.expense_breakdown?.map((item) => ({
    name: item.category,
    value: item.amount,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            <span>Monthly Income</span>
            <span className="p-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">Inflow</span>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            ₹{cashflow.monthly_income?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Total post-tax monthly take-home</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            <span>Total Monthly Expenses</span>
            <span className="p-1 rounded bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400">Outflow</span>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            ₹{cashflow.total_expenses?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Fixed: ₹{cashflow.total_fixed_expenses?.toLocaleString('en-IN')} | Variable: ₹{cashflow.total_variable_expenses?.toLocaleString('en-IN')}
          </p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            <span>Net Savings Capacity</span>
            <span className={`p-1 rounded text-xs font-bold ${cashflow.savings_capacity >= 0 ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400' : 'bg-red-50 text-red-600'}`}>
              Surplus
            </span>
          </div>
          <div className={`text-2xl font-black ${cashflow.savings_capacity >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600'}`}>
            ₹{cashflow.savings_capacity?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Free cash available for SIPs & debt reduction</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
            <span>Savings Rate</span>
            <span className="p-1 rounded bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">Rate</span>
          </div>
          <div className="text-2xl font-black text-blue-600 dark:text-blue-400">
            {cashflow.savings_rate}%
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${cashflow.savings_rate >= 30 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' : cashflow.savings_rate >= 20 ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'}`}>
              {cashflow.realism_status}
            </span>
          </div>
        </div>
      </div>

      {/* Expense Breakdown & Realism Note */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Chart */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
            Monthly Expense Distribution
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Visualizing where your hard-earned rupees flow every month.
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={breakdownData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {breakdownData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val) => `₹${Number(val).toLocaleString('en-IN')}`}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            <strong>Target Realism:</strong> {cashflow.realism_note}
          </div>
        </div>

        {/* Top 3 Cuts Card */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Scissors className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                Top 3 Discretionary Trims
              </h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Painless small trims that boost your investing velocity without diminishing living quality.
            </p>

            <div className="space-y-3">
              {cashflow.top_cuts?.map((cut, idx) => (
                <div key={idx} className="p-3.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-slate-900 dark:text-white">{cut.category}</span>
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                      +₹{cut.potential_saving?.toLocaleString('en-IN')}/mo
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    {cut.tip}
                  </p>
                </div>
              ))}
              {(!cashflow.top_cuts || cashflow.top_cuts.length === 0) && (
                <div className="p-4 text-center text-xs text-slate-400">
                  No high variable expenses recorded. Great expense discipline!
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
            💡 Rule: A 20% trim on discretionary spending can accelerate your goal completion by up to 14 months!
          </div>
        </div>
      </div>

      {/* Emergency Cushion Planning Section */}
      {emergency && (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Emergency Fund Shield (Rule of {emergency.target_months} Months)
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Target: {emergency.target_months} months of essential expenses (₹{emergency.essential_monthly_expenses?.toLocaleString('en-IN')}/mo survival cost).
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${emergency.gap === 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'}`}>
              {emergency.status}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium block">Target Safety Amount</span>
              <span className="text-lg font-bold text-slate-900 dark:text-white">
                ₹{emergency.target_amount?.toLocaleString('en-IN')}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">
                {emergency.target_months} months essential runway
              </span>
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium block">Current Reserves</span>
              <span className="text-lg font-bold text-slate-900 dark:text-white">
                ₹{emergency.current_amount?.toLocaleString('en-IN')}
              </span>
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 block mt-0.5">
                {emergency.months_covered} months covered
              </span>
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
              <span className="text-[11px] text-slate-400 font-medium block">Remaining Safety Gap</span>
              <span className={`text-lg font-bold ${emergency.gap > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600'}`}>
                ₹{emergency.gap?.toLocaleString('en-IN')}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">
                {emergency.gap > 0 ? `Fill in ~${emergency.months_to_fill} mos at ₹${emergency.recommended_monthly_allocation?.toLocaleString('en-IN')}/mo` : 'No funding required'}
              </span>
            </div>
          </div>

          {/* Where to keep it */}
          <div>
            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
              Where to Park Your Emergency Fund (Zero Capital Loss Architecture)
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {emergency.where_to_keep?.map((loc, i) => (
                <div key={i} className="p-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-slate-900 dark:text-white">{loc.vehicle}</span>
                    <span className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400">{loc.share}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    {loc.reason}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
