import React from 'react';
import { Shield, Globe, Moon, Sun, Download, UserCheck, Sparkles, ChevronDown } from 'lucide-react';

export default function Navbar({
  language,
  setLanguage,
  darkMode,
  setDarkMode,
  currentPersona,
  onSelectPersona,
  onDownloadReport,
  onOpenProfile,
  t
}) {
  return (
    <header className="sticky top-0 z-30 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200 dark:border-slate-800 transition-colors">
      {/* Top SEBI Disclaimer & Privacy Bar */}
      <div className="bg-emerald-50 dark:bg-emerald-950/50 border-b border-emerald-100 dark:border-emerald-900/50 px-4 py-1 text-xs text-emerald-800 dark:text-emerald-300 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-medium">
          <Shield className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>{t.disclaimer}</span>
        </div>
        <div className="text-slate-500 dark:text-slate-400 hidden sm:block text-[11px]">
          🔒 {t.privacyNote}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-md shadow-emerald-500/20 font-bold text-xl">
            अ
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 dark:text-white tracking-tight">{t.appName}</span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                Arthaton Demo
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">{t.appSubtitle}</p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Persona Switcher Pill */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden md:inline">{t.personas.title}:</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                {currentPersona === 'student' ? 'Student' : currentPersona === 'salaried_with_loan' ? 'Salaried' : 'Family'}
              </span>
              <ChevronDown className="w-3.5 h-3.5 opacity-60" />
            </button>
            <div className="absolute right-0 mt-1 w-56 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 p-1.5 hidden group-hover:block z-50">
              <div className="text-[11px] font-semibold text-slate-400 px-2 py-1 uppercase">Sample Personas</div>
              <button
                onClick={() => onSelectPersona('student')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex flex-col ${currentPersona === 'student' ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
              >
                <span>{t.personas.student}</span>
                <span className="text-[10px] text-slate-400 font-normal">21y/o intern, ₹22k/mo, no debt</span>
              </button>
              <button
                onClick={() => onSelectPersona('salaried_with_loan')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex flex-col ${currentPersona === 'salaried_with_loan' ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
              >
                <span>{t.personas.salaried}</span>
                <span className="text-[10px] text-slate-400 font-normal">28y/o engineer, ₹88k/mo, education + CC loan</span>
              </button>
              <button
                onClick={() => onSelectPersona('family_home_loan')}
                className={`w-full text-left px-2.5 py-2 rounded-lg text-xs transition flex flex-col ${currentPersona === 'family_home_loan' ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-semibold' : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'}`}
              >
                <span>{t.personas.family}</span>
                <span className="text-[10px] text-slate-400 font-normal">38y/o, ₹1.75L/mo, home loan + 3 dependents</span>
              </button>
            </div>
          </div>

          {/* Language Toggle */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 border border-slate-200 dark:border-slate-700 text-xs font-medium">
            <button
              onClick={() => setLanguage('en')}
              className={`px-2 py-1 rounded-md transition ${language === 'en' ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage('hi')}
              className={`px-2 py-1 rounded-md transition ${language === 'hi' ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
            >
              हिन्दी
            </button>
            <button
              onClick={() => setLanguage('ta')}
              className={`px-2 py-1 rounded-md transition ${language === 'ta' ? 'bg-white dark:bg-slate-700 text-emerald-600 dark:text-emerald-400 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}`}
            >
              தமிழ்
            </button>
          </div>

          {/* Dark / Light Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
            title="Toggle Dark Mode"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </button>

          {/* Download Plan Dropdown */}
          <div className="relative group">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition">
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Export Plan</span>
            </button>
            <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 p-1.5 hidden group-hover:block z-50">
              <button
                onClick={() => onDownloadReport('pdf')}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition flex items-center justify-between"
              >
                <span>Download PDF</span>
                <span className="text-[10px] bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300 px-1 rounded">PDF</span>
              </button>
              <button
                onClick={() => onDownloadReport('md')}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition flex items-center justify-between"
              >
                <span>Download Markdown</span>
                <span className="text-[10px] bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 px-1 rounded">MD</span>
              </button>
            </div>
          </div>

          {/* Edit Profile Button */}
          <button
            onClick={onOpenProfile}
            className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
            title="Edit Financial Profile"
          >
            <UserCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </button>
        </div>
      </div>
    </header>
  );
}
