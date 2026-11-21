import React, { useState, useEffect } from 'react';
import { Sliders, RefreshCw, ArrowRight, TrendingUp, Shield, Sparkles } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../api';

export default function WhatIfSimulator({ profile, initialAnalysis, t }) {
  const [extraSavings, setExtraSavings] = useState(5000);
  const [returnAdj, setReturnAdj] = useState(0);
  const [inflationAdj, setInflationAdj] = useState(0);
  const [retireAge, setRetireAge] = useState(profile?.retirement_age || 60);
  const [prepayMonthly, setPrepayMonthly] = useState(2000);

  const [simResult, setSimResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runSimulation = async () => {
    try {
      setLoading(true);
      const res = await api.simulateWhatIf({
        extra_monthly_savings: Number(extraSavings),
        return_adjustment: Number(returnAdj),
        inflation_adjustment: Number(inflationAdj),
        retirement_age_override: Number(retireAge),
        loan_prepayment_monthly: Number(prepayMonthly)
      });
      setSimResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [extraSavings, returnAdj, inflationAdj, retireAge, prepayMonthly]);

  const comp = simResult?.comparison;

  const chartData = comp
    ? [
        {
          name: 'Health Score',
          Before: comp.health_score.before,
          After: comp.health_score.after,
        },
        {
          name: 'Goals On Track %',
          Before: comp.goals_on_track_ratio.before,
          After: comp.goals_on_track_ratio.after,
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Interactive Financial What-If Simulator
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl">
            Tweak levers to instantly see the multi-decade ripple effects on your financial health score, debt freedom timeline, and retirement gap.
          </p>
        </div>

        <button
          onClick={() => {
            setExtraSavings(0);
            setReturnAdj(0);
            setInflationAdj(0);
            setRetireAge(profile?.retirement_age || 60);
            setPrepayMonthly(0);
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset Sliders</span>
        </button>
      </div>

      {/* Grid: Sliders on Left, Live Comparison on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sliders Panel */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Simulation Levers
          </h4>

          {/* Slider 1: Extra Savings */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              <span>Extra Monthly Savings</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                +₹{Number(extraSavings).toLocaleString('en-IN')}/mo
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="25000"
              step="1000"
              value={extraSavings}
              onChange={(e) => setExtraSavings(e.target.value)}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Trimming discretionary spend</span>
          </div>

          {/* Slider 2: Loan Prepayment */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              <span>Extra Loan Prepayment</span>
              <span className="text-rose-600 dark:text-rose-400 font-bold">
                +₹{Number(prepayMonthly).toLocaleString('en-IN')}/mo
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="20000"
              step="1000"
              value={prepayMonthly}
              onChange={(e) => setPrepayMonthly(e.target.value)}
              className="w-full accent-rose-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Accelerated principal paydown</span>
          </div>

          {/* Slider 3: Retirement Age */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              <span>Target Retirement Age</span>
              <span className="text-blue-600 dark:text-blue-400 font-bold">
                {retireAge} Years Old
              </span>
            </div>
            <input
              type="range"
              min="45"
              max="70"
              step="1"
              value={retireAge}
              onChange={(e) => setRetireAge(e.target.value)}
              className="w-full accent-blue-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">FIRE vs Extended Career Horizon</span>
          </div>

          {/* Slider 4: Market Return Adjustment */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              <span>Market Return Sensitivity</span>
              <span className="text-slate-800 dark:text-slate-200 font-bold">
                {returnAdj > 0 ? `+${returnAdj}` : returnAdj}% ({12 + Number(returnAdj)}% CAGR)
              </span>
            </div>
            <input
              type="range"
              min="-4"
              max="4"
              step="0.5"
              value={returnAdj}
              onChange={(e) => setReturnAdj(e.target.value)}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Bull vs Bear Market Cycles</span>
          </div>

          {/* Slider 5: Inflation Adjustment */}
          <div>
            <div className="flex justify-between text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
              <span>Inflation Rate Sensitivity</span>
              <span className="text-slate-800 dark:text-slate-200 font-bold">
                {inflationAdj > 0 ? `+${inflationAdj}` : inflationAdj}% ({6 + Number(inflationAdj)}% CPI)
              </span>
            </div>
            <input
              type="range"
              min="-3"
              max="4"
              step="0.5"
              value={inflationAdj}
              onChange={(e) => setInflationAdj(e.target.value)}
              className="w-full accent-purple-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-400">Macroeconomic inflation shift</span>
          </div>
        </div>

        {/* Live Comparison Output */}
        <div className="lg:col-span-7 space-y-5">
          {comp && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Card 1: Health Score */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <span className="text-[11px] text-slate-400 font-medium block">Financial Health Score</span>
                <div className="flex items-center gap-3 my-1">
                  <span className="text-lg text-slate-400 font-bold line-through">
                    {comp.health_score.before}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                    {comp.health_score.after}
                  </span>
                </div>
                <span className={`text-[11px] font-bold ${comp.health_score.delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {comp.health_score.delta >= 0 ? `+${comp.health_score.delta}` : comp.health_score.delta} pts shift
                </span>
              </div>

              {/* Card 2: Savings Capacity */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <span className="text-[11px] text-slate-400 font-medium block">Monthly Surplus Capacity</span>
                <div className="flex items-center gap-3 my-1">
                  <span className="text-sm text-slate-400 font-bold">
                    ₹{comp.savings_capacity.before?.toLocaleString('en-IN')}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className="text-2xl font-black text-blue-600 dark:text-blue-400">
                    ₹{comp.savings_capacity.after?.toLocaleString('en-IN')}
                  </span>
                </div>
                <span className="text-[11px] text-emerald-600 font-bold">
                  +₹{comp.savings_capacity.delta?.toLocaleString('en-IN')}/mo freed up
                </span>
              </div>

              {/* Card 3: Retirement Gap */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <span className="text-[11px] text-slate-400 font-medium block">Retirement Corpus Gap</span>
                <div className="flex items-center gap-3 my-1">
                  <span className="text-sm text-slate-400 font-bold">
                    ₹{(comp.retirement_corpus_gap.before / 10000000).toFixed(2)} Cr
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className="text-2xl font-black text-slate-900 dark:text-white">
                    ₹{(comp.retirement_corpus_gap.after / 10000000).toFixed(2)} Cr
                  </span>
                </div>
                <span className={`text-[11px] font-bold ${comp.retirement_corpus_gap.delta <= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {comp.retirement_corpus_gap.delta <= 0 ? `Reduced by ₹${Math.abs(comp.retirement_corpus_gap.delta / 100000).toFixed(1)} Lakh` : `Increased by ₹${(comp.retirement_corpus_gap.delta / 100000).toFixed(1)} Lakh`}
                </span>
              </div>

              {/* Card 4: Debt-Free Date */}
              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <span className="text-[11px] text-slate-400 font-medium block">Debt Payoff Horizon</span>
                <div className="flex items-center gap-3 my-1">
                  <span className="text-sm text-slate-400 font-bold">
                    {comp.debt_months_to_free.before} mos
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className="text-2xl font-black text-rose-600 dark:text-rose-400">
                    {comp.debt_months_to_free.after} mos
                  </span>
                </div>
                <span className="text-[11px] font-bold text-emerald-600">
                  {comp.debt_months_to_free.delta < 0 ? `Accelerated by ${Math.abs(comp.debt_months_to_free.delta)} months!` : 'On scheduled pace'}
                </span>
              </div>
            </div>
          )}

          {/* Visual Comparison Bar Chart */}
          <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Before vs After Trajectory Comparison
            </h4>
            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Bar dataKey="Before" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="After" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
