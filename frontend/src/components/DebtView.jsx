import React from 'react';
import { CreditCard, Zap, Flame, Snowflake, ArrowDownRight, Award, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function DebtView({ debt, t }) {
  if (!debt) return null;

  if (!debt.has_loans) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-4">
          <Award className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">
          100% Debt-Free Status!
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto mb-4">
          You have zero active loan obligations or EMIs. 100% of your savings capacity can be directed towards compounding in equities, retirement, and your priority goals.
        </p>
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
          <ShieldCheck className="w-4 h-4" /> DTI: 0.0% (Perfect)
        </span>
      </div>
    );
  }

  const loans = debt.loans_ranked_by_interest || [];
  const payFirst = debt.pay_this_first;
  const avalanche = debt.avalanche_plan || {};
  const snowball = debt.snowball_plan || {};
  const prepay = debt.prepayment_comparison || {};

  return (
    <div className="space-y-6">
      {/* Top Banner: Pay This First Recommendation */}
      {payFirst && (
        <div className="bg-gradient-to-r from-rose-500/10 via-amber-500/10 to-transparent dark:from-rose-950/40 dark:via-amber-950/20 rounded-2xl p-6 border border-rose-200 dark:border-rose-900/60 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-rose-500 text-white flex items-center justify-center shadow-md shadow-rose-500/20 shrink-0">
                <Zap className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-rose-600 dark:text-rose-400 bg-rose-100 dark:bg-rose-950 px-2 py-0.5 rounded">
                  Urgent Priority Action
                </span>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                  Pay This First: {payFirst.loan_name}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 max-w-2xl leading-relaxed">
                  {payFirst.reason}
                </p>
              </div>
            </div>

            <div className="text-right sm:border-l sm:border-slate-200 dark:sm:border-slate-800 sm:pl-6 shrink-0">
              <span className="text-xs text-slate-400 block font-medium">Interest Rate</span>
              <span className="text-2xl font-black text-rose-600 dark:text-rose-400">
                {payFirst.interest_rate}% p.a.
              </span>
              <span className="text-[11px] text-slate-500 block">
                Outstanding: ₹{payFirst.outstanding_amount?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* DTI and Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Debt-to-Income (DTI)
          </span>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-black ${debt.dti_ratio <= 35 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600'}`}>
              {debt.dti_ratio}%
            </span>
            <span className="text-xs font-bold text-slate-500">
              ({debt.dti_status})
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">{debt.dti_note}</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Total Outstanding Debt
          </span>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            ₹{debt.total_debt?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Across {loans.length} active credit instruments</p>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Total Monthly Loan EMIs
          </span>
          <div className="text-2xl font-black text-slate-900 dark:text-white">
            ₹{debt.total_emi?.toLocaleString('en-IN')}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Committed monthly outflow before discretionary spend</p>
        </div>
      </div>

      {/* Ranked Loans Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
        <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">
          Loan Matrix Ranked by Interest Rate (Debt Avalanche Order)
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Ordered from highest interest rate to lowest. Mathematical optimization dictates directing surplus rupees to the top first.
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-semibold uppercase text-[10px]">
                <th className="pb-3">Rank / Loan</th>
                <th className="pb-3">Type</th>
                <th className="pb-3">Interest Rate</th>
                <th className="pb-3">Outstanding Balance</th>
                <th className="pb-3">Monthly EMI</th>
                <th className="pb-3">Remaining Tenure</th>
                <th className="pb-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loans.map((loan, idx) => (
                <tr key={loan.id || idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                  <td className="py-3 font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-[10px] font-bold flex items-center justify-center text-slate-600 dark:text-slate-300">
                      {idx + 1}
                    </span>
                    <span>{loan.name}</span>
                  </td>
                  <td className="py-3 text-slate-500 dark:text-slate-400 capitalize">{loan.type?.replace('_', ' ')}</td>
                  <td className="py-3 font-bold text-rose-600 dark:text-rose-400">{loan.interest_rate}%</td>
                  <td className="py-3 font-medium text-slate-800 dark:text-slate-200">₹{loan.outstanding_amount?.toLocaleString('en-IN')}</td>
                  <td className="py-3 text-slate-700 dark:text-slate-300">₹{loan.emi?.toLocaleString('en-IN')}/mo</td>
                  <td className="py-3 text-slate-500">{loan.remaining_tenure} months</td>
                  <td className="py-3">
                    {idx === 0 ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300">
                        Pay First
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        Maintain EMI
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Avalanche vs Snowball Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Avalanche */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border-2 border-emerald-500/40 dark:border-emerald-500/30 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-emerald-500 text-white text-[10px] uppercase font-bold px-3 py-1 rounded-bl-xl tracking-wider">
            Recommended
          </div>
          <div className="flex items-center gap-2 mb-2">
            <Flame className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              {avalanche.strategy}
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            {avalanche.description}
          </p>

          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Payoff Sequence</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">{avalanche.order?.join(' → ')}</span>
            </div>
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Debt-Free Horizon</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">{avalanche.months_to_debt_free} months</span>
            </div>
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Net Interest Saved</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                +₹{avalanche.interest_saved_vs_baseline?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>

        {/* Snowball */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Snowflake className="w-5 h-5 text-blue-500" />
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              {snowball.strategy}
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            {snowball.description}
          </p>

          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Payoff Sequence</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">{snowball.order?.join(' → ')}</span>
            </div>
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Debt-Free Horizon</span>
              <span className="font-bold text-slate-700 dark:text-slate-300">{snowball.months_to_debt_free} months</span>
            </div>
            <div className="flex justify-between text-xs py-2 border-b border-slate-100 dark:border-slate-800">
              <span className="text-slate-500">Net Interest Saved</span>
              <span className="font-bold text-slate-700 dark:text-slate-300">
                +₹{snowball.interest_saved_vs_baseline?.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
