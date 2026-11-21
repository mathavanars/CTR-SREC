import React from 'react';
import { Clock, ShieldCheck, TrendingUp, AlertCircle, ArrowUpRight, CheckCircle2 } from 'lucide-react';

export default function RetirementView({ retirement, t }) {
  if (!retirement) return null;

  const assumptions = retirement.assumptions || {};

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Retirement Freedom Diagnostics
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Retire at age {retirement.retirement_age} ({retirement.years_to_retirement} years runway). Modeling inflation-adjusted lifestyle sustainability through age {assumptions.life_expectancy || 85}.
          </p>
        </div>

        <div className="text-right border-t sm:border-t-0 sm:border-l border-slate-100 dark:border-slate-800 pt-3 sm:pt-0 sm:pl-6 shrink-0">
          <span className="text-[11px] text-slate-400 font-medium block">Retirement Readiness</span>
          <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
            {retirement.readiness_percentage}%
          </span>
          <span className="text-[10px] text-slate-400 block">funded at current pace</span>
        </div>
      </div>

      {/* 4 Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Target Corpus Needed
          </span>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            ₹{(retirement.target_corpus / 10000000).toFixed(2)} Cr
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Based on ₹{retirement.future_monthly_expense?.toLocaleString('en-IN')}/mo future expense
          </p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Projected Corpus at Current Pace
          </span>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
            ₹{(retirement.projected_corpus_at_current_pace / 10000000).toFixed(2)} Cr
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Growth of current savings + existing SIPs
          </p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Retirement Corpus Shortfall
          </span>
          <div className={`text-2xl font-black ${retirement.corpus_gap > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600'}`}>
            ₹{(retirement.corpus_gap / 10000000).toFixed(2)} Cr
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            {retirement.corpus_gap > 0 ? 'Remaining deficit to close' : 'Surplus corpus projected'}
          </p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Extra Monthly SIP Required
          </span>
          <div className="text-2xl font-black text-blue-600 dark:text-blue-400">
            ₹{retirement.additional_monthly_sip_needed?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            In broad index funds / PPF / NPS to bridge gap
          </p>
        </div>
      </div>

      {/* Assumptions Transparency Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
          Transparent Actuarial Assumptions (Clearly labeled from config)
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
            <span className="text-slate-400 block text-[11px]">Assumed Inflation</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{assumptions.inflation_rate}% p.a.</span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
            <span className="text-slate-400 block text-[11px]">Pre-Retirement CAGR</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{assumptions.pre_retirement_cagr}% p.a.</span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
            <span className="text-slate-400 block text-[11px]">Post-Retire Yield</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{assumptions.post_retirement_cagr}% p.a.</span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
            <span className="text-slate-400 block text-[11px]">Safe Withdrawal</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{assumptions.safe_withdrawal_rate}% / year</span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800">
            <span className="text-slate-400 block text-[11px]">Life Expectancy</span>
            <span className="font-bold text-slate-800 dark:text-slate-200">{assumptions.life_expectancy} Years</span>
          </div>
        </div>
      </div>
    </div>
  );
}
