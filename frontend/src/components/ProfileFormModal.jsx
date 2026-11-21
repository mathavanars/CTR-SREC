import React, { useState } from 'react';
import { X, Check, ArrowRight, ArrowLeft, Plus, Trash2, HelpCircle, ShieldCheck } from 'lucide-react';

export default function ProfileFormModal({ isOpen, onClose, initialProfile, onSave, t }) {
  if (!isOpen) return null;

  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState({
    age: initialProfile?.age || 28,
    retirement_age: initialProfile?.retirement_age || 60,
    dependents: initialProfile?.dependents || 0,
    risk_appetite: initialProfile?.risk_appetite || 'Medium',
    monthly_income: initialProfile?.monthly_income || 50000,
    savings: initialProfile?.savings || 20000,
    fixed_expenses: initialProfile?.fixed_expenses || { house_rent: 15000, utilities: 3000 },
    variable_expenses: initialProfile?.variable_expenses || { groceries: 10000, dining_travel: 5000 },
    investments: initialProfile?.investments || [],
    loans: initialProfile?.loans || [],
    goals: initialProfile?.goals || []
  });

  const [quizMode, setQuizMode] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});

  // 5-Question Risk Quiz
  const riskQuestions = [
    {
      id: 'q1',
      text: 'If the stock market crashes by 25% in 3 months, what is your initial reaction?',
      options: [
        { label: 'Panic and withdraw everything into a bank FD', score: 1 },
        { label: 'Feel nervous but hold my current investments', score: 2 },
        { label: 'Excited! Treat it as a discount and buy more index units', score: 3 }
      ]
    },
    {
      id: 'q2',
      text: 'What is your primary investment goal?',
      options: [
        { label: '100% capital safety, even if returns lag inflation', score: 1 },
        { label: 'Steady moderate growth beating inflation with balanced risk', score: 2 },
        { label: 'Maximum long-term wealth compounding over 10+ years', score: 3 }
      ]
    },
    {
      id: 'q3',
      text: 'How stable is your current primary income source?',
      options: [
        { label: 'Irregular or freelance with uncertain cashflow', score: 1 },
        { label: 'Stable corporate or public sector salary', score: 2 },
        { label: 'Very stable with multiple household earning members', score: 3 }
      ]
    },
    {
      id: 'q4',
      text: 'What is your investment time horizon for major wealth accumulation?',
      options: [
        { label: 'Short (under 3 years)', score: 1 },
        { label: 'Medium (3 to 7 years)', score: 2 },
        { label: 'Long (7 to 25+ years)', score: 3 }
      ]
    },
    {
      id: 'q5',
      text: 'Have you previously invested in Mutual Funds or Equities?',
      options: [
        { label: 'Never, this is my first time exploring investments', score: 1 },
        { label: 'Yes, I have an active SIP in index/hybrid funds', score: 2 },
        { label: 'Experienced investor with diversified portfolio', score: 3 }
      ]
    }
  ];

  const computeQuizScore = () => {
    let total = 0;
    Object.values(quizAnswers).forEach((sc) => {
      total += sc;
    });
    if (total <= 7) return 'Low';
    if (total <= 11) return 'Medium';
    return 'High';
  };

  const applyQuizResult = () => {
    const result = computeQuizScore();
    setProfile({ ...profile, risk_appetite: result });
    setQuizMode(false);
  };

  // Sub-items add/delete handlers
  const addLoan = () => {
    setProfile({
      ...profile,
      loans: [
        ...profile.loans,
        {
          name: 'Personal Loan',
          type: 'personal',
          outstanding_amount: 100000,
          interest_rate: 12.5,
          emi: 4000,
          remaining_tenure: 30
        }
      ]
    });
  };

  const removeLoan = (index) => {
    setProfile({
      ...profile,
      loans: profile.loans.filter((_, i) => i !== index)
    });
  };

  const addInvestment = () => {
    setProfile({
      ...profile,
      investments: [
        ...profile.investments,
        {
          name: 'Nifty Index SIP',
          type: 'mutual_fund',
          current_value: 25000,
          monthly_contribution: 2500
        }
      ]
    });
  };

  const removeInvestment = (index) => {
    setProfile({
      ...profile,
      investments: profile.investments.filter((_, i) => i !== index)
    });
  };

  const addGoal = () => {
    setProfile({
      ...profile,
      goals: [
        ...profile.goals,
        {
          name: 'Home Downpayment',
          category: 'house',
          target_amount: 500000,
          current_saved: 50000,
          target_date: '2028-12',
          priority: 'High'
        }
      ]
    });
  };

  const removeGoal = (index) => {
    setProfile({
      ...profile,
      goals: profile.goals.filter((_, i) => i !== index)
    });
  };

  const handleSave = () => {
    onSave(profile);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl w-full max-w-3xl overflow-hidden my-8">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Personal Financial Questionnaire
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Step {step} of 4 • Validated inputs for deterministic analysis
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 max-h-[65vh] overflow-y-auto space-y-5">
          {/* STEP 1: Demographics & Risk */}
          {step === 1 && (
            <div className="space-y-4">
              <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                1. Personal Demographics & Risk Profile
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 block mb-1">
                    Current Age
                  </label>
                  <input
                    type="number"
                    min="18"
                    max="80"
                    value={profile.age}
                    onChange={(e) => setProfile({ ...profile, age: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 block mb-1">
                    Planned Retirement Age
                  </label>
                  <input
                    type="number"
                    min="35"
                    max="80"
                    value={profile.retirement_age}
                    onChange={(e) => setProfile({ ...profile, retirement_age: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 block mb-1">
                    Dependents Count
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={profile.dependents}
                    onChange={(e) => setProfile({ ...profile, dependents: Number(e.target.value) })}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Risk Appetite Selection & Quiz */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Risk Appetite
                  </label>
                  <button
                    type="button"
                    onClick={() => setQuizMode(!quizMode)}
                    className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    {quizMode ? 'Back to Direct Selection' : '🎯 Take 5-Question Risk Quiz'}
                  </button>
                </div>

                {!quizMode ? (
                  <div className="grid grid-cols-3 gap-3">
                    {['Low', 'Medium', 'High'].map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setProfile({ ...profile, risk_appetite: r })}
                        className={`p-3 rounded-xl border text-xs font-bold transition ${
                          profile.risk_appetite === r
                            ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-500 text-emerald-700 dark:text-emerald-300 shadow-xs'
                            : 'bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300'
                        }`}
                      >
                        {r} Risk
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-700 space-y-4">
                    <h5 className="font-bold text-xs text-slate-900 dark:text-white uppercase tracking-wider">
                      5-Question Behavioral Risk Evaluation
                    </h5>
                    {riskQuestions.map((q, i) => (
                      <div key={q.id} className="space-y-1.5">
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {i + 1}. {q.text}
                        </p>
                        <div className="space-y-1 pl-2">
                          {q.options.map((opt, oIdx) => (
                            <label
                              key={oIdx}
                              className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer"
                            >
                              <input
                                type="radio"
                                name={q.id}
                                checked={quizAnswers[q.id] === opt.score}
                                onChange={() => setQuizAnswers({ ...quizAnswers, [q.id]: opt.score })}
                                className="accent-emerald-500"
                              />
                              <span>{opt.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={applyQuizResult}
                      disabled={Object.keys(quizAnswers).length < 5}
                      className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white font-bold rounded-xl text-xs transition"
                    >
                      Calculate My Risk Profile
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 2: Cashflow & Budget */}
          {step === 2 && (
            <div className="space-y-4">
              <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                2. Monthly Cashflow & Expenses Breakdown
              </h4>

              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 block mb-1">
                  Monthly Take-Home Inflow (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={profile.monthly_income}
                  onChange={(e) => setProfile({ ...profile, monthly_income: Number(e.target.value) })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300 block mb-1">
                  Liquid Bank Savings & Cash Balance (₹)
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={profile.savings}
                  onChange={(e) => setProfile({ ...profile, savings: Number(e.target.value) })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-xs text-slate-900 dark:text-white"
                />
              </div>

              {/* Fixed Expenses */}
              <div>
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-2">
                  Fixed Obligations (Rent, Bills, Insurance, Subscriptions)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(profile.fixed_expenses).map(([key, val]) => (
                    <div key={key}>
                      <span className="text-[11px] text-slate-400 capitalize block mb-0.5">
                        {key.replace('_', ' ')} (₹)
                      </span>
                      <input
                        type="number"
                        min="0"
                        value={val}
                        onChange={(e) =>
                          setProfile({
                            ...profile,
                            fixed_expenses: { ...profile.fixed_expenses, [key]: Number(e.target.value) }
                          })
                        }
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2 text-xs"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Variable Expenses */}
              <div>
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-2">
                  Variable Discretionary Spend (Food, Travel, Shopping, Other)
                </span>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(profile.variable_expenses).map(([key, val]) => (
                    <div key={key}>
                      <span className="text-[11px] text-slate-400 capitalize block mb-0.5">
                        {key.replace('_', ' ')} (₹)
                      </span>
                      <input
                        type="number"
                        min="0"
                        value={val}
                        onChange={(e) =>
                          setProfile({
                            ...profile,
                            variable_expenses: { ...profile.variable_expenses, [key]: Number(e.target.value) }
                          })
                        }
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2 text-xs"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: Loans & Existing Investments */}
          {step === 3 && (
            <div className="space-y-5">
              <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                3. Loans & Liabilities & Existing Investments
              </h4>

              {/* Loans List */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                    Loans & Credit Obligations
                  </span>
                  <button
                    type="button"
                    onClick={addLoan}
                    className="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Loan</span>
                  </button>
                </div>

                {profile.loans.map((loan, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700 mb-2.5 grid grid-cols-6 gap-2 items-center text-xs"
                  >
                    <div className="col-span-2">
                      <input
                        type="text"
                        value={loan.name}
                        onChange={(e) => {
                          const updated = [...profile.loans];
                          updated[idx].name = e.target.value;
                          setProfile({ ...profile, loans: updated });
                        }}
                        placeholder="Loan Name"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        value={loan.outstanding_amount}
                        onChange={(e) => {
                          const updated = [...profile.loans];
                          updated[idx].outstanding_amount = Number(e.target.value);
                          setProfile({ ...profile, loans: updated });
                        }}
                        placeholder="Principal"
                        title="Outstanding Amount"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        value={loan.interest_rate}
                        onChange={(e) => {
                          const updated = [...profile.loans];
                          updated[idx].interest_rate = Number(e.target.value);
                          setProfile({ ...profile, loans: updated });
                        }}
                        placeholder="Rate %"
                        title="Interest Rate %"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        value={loan.emi}
                        onChange={(e) => {
                          const updated = [...profile.loans];
                          updated[idx].emi = Number(e.target.value);
                          setProfile({ ...profile, loans: updated });
                        }}
                        placeholder="EMI ₹"
                        title="Monthly EMI"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => removeLoan(idx)}
                        className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
                {profile.loans.length === 0 && (
                  <p className="text-xs text-slate-400 italic">No loans added. (Debt-free)</p>
                )}
              </div>

              {/* Investments List */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                    Existing Investments (SIP, PPF, FD, EPF, Gold)
                  </span>
                  <button
                    type="button"
                    onClick={addInvestment}
                    className="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Investment</span>
                  </button>
                </div>

                {profile.investments.map((inv, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700 mb-2.5 grid grid-cols-5 gap-2 items-center text-xs"
                  >
                    <div className="col-span-2">
                      <input
                        type="text"
                        value={inv.name}
                        onChange={(e) => {
                          const updated = [...profile.investments];
                          updated[idx].name = e.target.value;
                          setProfile({ ...profile, investments: updated });
                        }}
                        placeholder="Investment Name"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        value={inv.current_value}
                        onChange={(e) => {
                          const updated = [...profile.investments];
                          updated[idx].current_value = Number(e.target.value);
                          setProfile({ ...profile, investments: updated });
                        }}
                        placeholder="Current Value"
                        title="Current Value ₹"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div>
                      <input
                        type="number"
                        value={inv.monthly_contribution}
                        onChange={(e) => {
                          const updated = [...profile.investments];
                          updated[idx].monthly_contribution = Number(e.target.value);
                          setProfile({ ...profile, investments: updated });
                        }}
                        placeholder="Monthly SIP"
                        title="Monthly SIP ₹"
                        className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => removeInvestment(idx)}
                        className="p-1.5 text-rose-500 hover:bg-rose-50 rounded-lg transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* STEP 4: Life Goals */}
          {step === 4 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h4 className="font-bold text-slate-800 dark:text-slate-200 text-sm">
                    4. Life Goals & Target Milestones
                  </h4>
                  <p className="text-xs text-slate-400">
                    Add goals such as buying a house down payment, education, car, or emergency reserves.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={addGoal}
                  className="flex items-center gap-1 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Goal</span>
                </button>
              </div>

              {profile.goals.map((goal, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700 mb-3 space-y-2 text-xs"
                >
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <input
                      type="text"
                      value={goal.name}
                      onChange={(e) => {
                        const updated = [...profile.goals];
                        updated[idx].name = e.target.value;
                        setProfile({ ...profile, goals: updated });
                      }}
                      placeholder="Goal Name (e.g. EV Car)"
                      className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5 font-semibold"
                    />
                    <input
                      type="number"
                      value={goal.target_amount}
                      onChange={(e) => {
                        const updated = [...profile.goals];
                        updated[idx].target_amount = Number(e.target.value);
                        setProfile({ ...profile, goals: updated });
                      }}
                      placeholder="Target Amount ₹"
                      className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                    />
                    <input
                      type="text"
                      value={goal.target_date}
                      onChange={(e) => {
                        const updated = [...profile.goals];
                        updated[idx].target_date = e.target.value;
                        setProfile({ ...profile, goals: updated });
                      }}
                      placeholder="Target Date (YYYY-MM)"
                      className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Priority:</span>
                      {['High', 'Medium', 'Low'].map((p) => (
                        <button
                          key={p}
                          type="button"
                          onClick={() => {
                            const updated = [...profile.goals];
                            updated[idx].priority = p;
                            setProfile({ ...profile, goals: updated });
                          }}
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            goal.priority === p
                              ? 'bg-emerald-600 text-white'
                              : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>

                    <button
                      type="button"
                      onClick={() => removeGoal(idx)}
                      className="p-1 text-rose-500 hover:bg-rose-50 rounded transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
          {step > 1 ? (
            <button
              type="button"
              onClick={() => setStep(step - 1)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={() => setStep(step + 1)}
              className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-sm"
            >
              <span>Continue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSave}
              className="flex items-center gap-1.5 px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-md shadow-emerald-500/20"
            >
              <Check className="w-4 h-4" />
              <span>Generate Full Financial Plan</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
