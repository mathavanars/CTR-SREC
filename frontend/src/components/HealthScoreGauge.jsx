import React, { useState } from 'react';
import { HelpCircle, ChevronDown, ChevronUp, AlertCircle, CheckCircle2, TrendingUp, ShieldCheck } from 'lucide-react';

export default function HealthScoreGauge({ healthScore, cashflow, debt, emergency, t }) {
  const [expandedSubScore, setExpandedSubScore] = useState(null);

  if (!healthScore) return null;

  const score = healthScore.score || 0;
  const band = healthScore.band || 'Fair';
  const summary = healthScore.summary || '';
  const subScores = healthScore.sub_scores || [];

  // Determine color theme based on score
  let badgeColor = 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border-amber-300 dark:border-amber-800';
  let strokeColor = '#f59e0b';
  if (score >= 80) {
    badgeColor = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
    strokeColor = '#10b981';
  } else if (score >= 60) {
    badgeColor = 'bg-teal-100 text-teal-800 dark:bg-teal-950/70 dark:text-teal-300 border-teal-300 dark:border-teal-800';
    strokeColor = '#14b8a6';
  } else if (score < 40) {
    badgeColor = 'bg-rose-100 text-rose-800 dark:bg-rose-950/70 dark:text-rose-300 border-rose-300 dark:border-rose-800';
    strokeColor = '#f43f5e';
  }

  // Semi-circle SVG gauge calculation
  const radius = 80;
  const circumference = Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="space-y-6">
      {/* Main Score Hero Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm transition">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          {/* Gauge Widget */}
          <div className="md:col-span-5 flex flex-col items-center justify-center p-4">
            <div className="relative w-48 h-28 flex items-end justify-center">
              <svg className="w-48 h-48 -rotate-180 transform overflow-visible" viewBox="0 0 200 200">
                {/* Background Track */}
                <circle
                  cx="100"
                  cy="100"
                  r={radius}
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="16"
                  strokeDasharray={`${circumference} ${circumference}`}
                  strokeDashoffset="0"
                  className="text-slate-100 dark:text-slate-800"
                  strokeLinecap="round"
                />
                {/* Filled Gauge */}
                <circle
                  cx="100"
                  cy="100"
                  r={radius}
                  fill="transparent"
                  stroke={strokeColor}
                  strokeWidth="16"
                  strokeDasharray={`${circumference} ${circumference}`}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              {/* Center Score */}
              <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
                <span className="text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                  {score}
                </span>
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                  Out of 100
                </span>
              </div>
            </div>

            <div className="mt-4 flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${badgeColor}`}>
                {band}
              </span>
            </div>
          </div>

          {/* Score Explanation & High-Impact Insights */}
          <div className="md:col-span-7 space-y-3">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Financial Health Diagnostics
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {summary}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-800">
                <span className="text-[11px] text-slate-400 font-medium block">Savings Rate</span>
                <span className="text-base font-bold text-slate-900 dark:text-white">
                  {cashflow?.savings_rate || 0}%
                </span>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-800">
                <span className="text-[11px] text-slate-400 font-medium block">Emergency Runway</span>
                <span className="text-base font-bold text-slate-900 dark:text-white">
                  {emergency?.months_covered || 0} mo
                </span>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-800">
                <span className="text-[11px] text-slate-400 font-medium block">Debt-to-Income (DTI)</span>
                <span className="text-base font-bold text-slate-900 dark:text-white">
                  {debt?.dti_ratio || 0}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sub-Scores Matrix */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Health Sub-Scores & Determinants
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Each sub-score is independently evaluated against Indian financial resilience benchmarks.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {subScores.map((sub, idx) => {
            const isExpanded = expandedSubScore === idx;
            const subScore = sub.score;
            let barColor = 'bg-amber-500';
            if (subScore >= 80) barColor = 'bg-emerald-500';
            else if (subScore < 40) barColor = 'bg-rose-500';

            return (
              <div
                key={sub.key || idx}
                className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 transition"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-slate-800 dark:text-slate-200">
                      {sub.name}
                    </span>
                    <span className="text-[10px] text-slate-400 font-medium">
                      (Weight: {sub.weight})
                    </span>
                  </div>
                  <span className="font-bold text-xs text-slate-900 dark:text-white">
                    {subScore} / 100
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden mb-2">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                    style={{ width: `${subScore}%` }}
                  />
                </div>

                {/* One-line reason */}
                <p className="text-xs text-slate-600 dark:text-slate-300 mb-2 leading-relaxed">
                  {sub.reason}
                </p>

                {/* Expandable "Why this advice?" */}
                <button
                  onClick={() => setExpandedSubScore(isExpanded ? null : idx)}
                  className="flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  <span>{t.common.whyThis}</span>
                  {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {isExpanded && (
                  <div className="mt-2.5 p-2.5 bg-white dark:bg-slate-800 rounded-lg text-xs text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 space-y-1">
                    <p>
                      <strong>Scoring Rule:</strong> Built with deterministic weights calibrated for Indian families (savings rate, emergency cushion, debt-to-income, asset diversification, goal feasibility, and term/health insurance buffer).
                    </p>
                    <p>
                      <strong>How to improve:</strong> Direct cash surplus towards this sub-pillar in the Action Checklist to push your score towards 90+.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
