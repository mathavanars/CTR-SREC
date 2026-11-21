import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { PieChart as PieIcon, ShieldAlert, Sparkles, AlertTriangle, Layers, Info } from 'lucide-react';

export default function AllocationView({ allocation, t }) {
  if (!allocation) return null;

  const categories = allocation.categories || [];
  const rationale = allocation.rationale || '';
  const realEstateGuidance = allocation.real_estate_guidance;

  const COLORS = {
    equity_index: '#10b981', // Emerald
    ppf_nps: '#3b82f6',     // Blue
    fd_debt: '#8b5cf6',     // Purple
    emergency_liquid: '#06b6d4', // Cyan
    gold: '#f59e0b'         // Amber
  };

  const pieData = categories.map((c) => ({
    name: c.name.split(' (')[0],
    fullName: c.name,
    value: c.percentage,
    amount: c.monthly_amount,
    categoryKey: c.category,
    returnRate: c.expected_return
  }));

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                Target Asset Allocation (Category-Level Only)
              </h3>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
              Transparent rule-based allocation based on your age ({allocation.age_applied}) and {allocation.risk_appetite_applied} risk profile. We recommend broad asset classes, never specific commercial brands or speculative stock picks.
            </p>
          </div>
          <div className="px-3 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 shrink-0">
            Rule: Age {allocation.age_applied} Baseline
          </div>
        </div>

        {/* Chart + Rationale */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          <div className="lg:col-span-6 h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[entry.categoryKey] || '#64748b'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val, name, item) => [
                    `${val}% (₹${item.payload.amount?.toLocaleString('en-IN')}/mo)`,
                    item.payload.fullName
                  ]}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="lg:col-span-6 space-y-3">
            <div className="p-4 bg-emerald-50/60 dark:bg-emerald-950/40 rounded-xl border border-emerald-100 dark:border-emerald-900/40 text-xs text-emerald-900 dark:text-emerald-200 leading-relaxed">
              <span className="font-bold block mb-1">Why this split?</span>
              {rationale}
            </div>

            <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300">
              <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-1">
                Zero Stock-Tipping Pledge
              </span>
              Empirical market studies prove that 90%+ of portfolio return variance is determined by category-level asset allocation, not stock picking.
            </div>
          </div>
        </div>
      </div>

      {/* Asset Category Details Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {categories.map((cat, idx) => (
          <div
            key={cat.category || idx}
            className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  {cat.name}
                </span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-black text-white"
                  style={{ backgroundColor: COLORS[cat.category] || '#64748b' }}
                >
                  {cat.percentage}%
                </span>
              </div>

              <div className="p-2.5 bg-slate-50 dark:bg-slate-800/40 rounded-xl mb-3 flex items-center justify-between text-xs">
                <span className="text-slate-400">Monthly Inflow</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  ₹{cat.monthly_amount?.toLocaleString('en-IN')}/mo
                </span>
              </div>

              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-3">
                {cat.purpose}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
              <span>Assumed Return:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">{cat.expected_return}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Real Estate Illiquidity Alert */}
      {realEstateGuidance && (
        <div className="bg-amber-50 dark:bg-amber-950/30 rounded-2xl p-5 border border-amber-200 dark:border-amber-900/50 shadow-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-amber-900 dark:text-amber-200 uppercase tracking-wider">
              Real Estate / Land Guidance: {realEstateGuidance.status}
            </h4>
            <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
              {realEstateGuidance.reason}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
