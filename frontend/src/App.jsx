import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import HealthScoreGauge from './components/HealthScoreGauge';
import SavingsView from './components/SavingsView';
import DebtView from './components/DebtView';
import GoalsView from './components/GoalsView';
import AllocationView from './components/AllocationView';
import RetirementView from './components/RetirementView';
import ActionPlanView from './components/ActionPlanView';
import WhatIfSimulator from './components/WhatIfSimulator';
import CoachChat from './components/CoachChat';
import ProfileFormModal from './components/ProfileFormModal';
import AuthModal from './components/AuthModal';
import { translations } from './translations';
import { api, getStoredToken, setStoredToken, setStoredUser, getStoredUser } from './api';
import { Shield, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';

export default function App() {
  const [language, setLanguage] = useState('en');
  const [darkMode, setDarkMode] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const [currentUser, setCurrentUser] = useState(getStoredUser());
  const [currentPersona, setCurrentPersona] = useState('salaried_with_loan');
  
  const [profile, setProfile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const t = translations[language] || translations.en;

  // Toggle Dark Mode class on document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  // Initial Demo Authentication & Load
  useEffect(() => {
    const initApp = async () => {
      try {
        setLoading(true);
        setError(null);

        // Ensure user is authenticated (create/login demo session if token absent)
        let token = getStoredToken();
        if (!token) {
          try {
            const loginRes = await api.login('demo@arthmitra.ai', 'demo12345');
            setStoredToken(loginRes.access_token);
            setStoredUser(loginRes.user);
            setCurrentUser(loginRes.user);
          } catch {
            const regRes = await api.register('demo@arthmitra.ai', 'demo12345', 'Demo Investor');
            setStoredToken(regRes.access_token);
            setStoredUser(regRes.user);
            setCurrentUser(regRes.user);
          }
        }

        // Fetch profile & analysis
        const [profData, anaData] = await Promise.all([
          api.getProfile(),
          api.getFullAnalysis(),
        ]);
        setProfile(profData);
        setAnalysis(anaData);
      } catch (err) {
        console.error('Initialization error:', err);
        setError(err.message || 'Unable to connect to ArthMitra backend. Please ensure the server is active.');
      } finally {
        setLoading(false);
      }
    };

    initApp();
  }, []);

  // Switch persona
  const handleSelectPersona = async (personaId) => {
    try {
      setLoading(true);
      setCurrentPersona(personaId);
      await api.loadPersona(personaId);
      const [profData, anaData] = await Promise.all([
        api.getProfile(),
        api.getFullAnalysis(),
      ]);
      setProfile(profData);
      setAnalysis(anaData);
    } catch (err) {
      console.error(err);
      setError('Failed to switch persona.');
    } finally {
      setLoading(false);
    }
  };

  // Save updated profile
  const handleSaveProfile = async (updatedProfile) => {
    try {
      setLoading(true);
      await api.updateProfile(updatedProfile);
      const [profData, anaData] = await Promise.all([
        api.getProfile(),
        api.getFullAnalysis(),
      ]);
      setProfile(profData);
      setAnalysis(anaData);
    } catch (err) {
      console.error(err);
      setError('Failed to update financial profile.');
    } finally {
      setLoading(false);
    }
  };

  // Download Report
  const handleDownloadReport = async (format) => {
    try {
      const blob = await api.downloadReport(format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ArthMitra_Plan_${currentPersona}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Could not download report: ' + err.message);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col transition-colors duration-200">
      {/* Top Navbar */}
      <Navbar
        language={language}
        setLanguage={setLanguage}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        currentPersona={currentPersona}
        onSelectPersona={handleSelectPersona}
        onDownloadReport={handleDownloadReport}
        onOpenProfile={() => setIsProfileModalOpen(true)}
        t={t}
      />

      {/* Main Body */}
      <div className="flex-1 flex flex-col md:flex-row max-w-7xl w-full mx-auto">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} t={t} />

        {/* Content Pane */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          {/* Error Notice */}
          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 flex items-center justify-between text-xs text-rose-700 dark:text-rose-300">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="px-3 py-1 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700 transition"
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading Skeleton */}
          {loading && (
            <div className="space-y-6 animate-pulse">
              <div className="h-44 bg-slate-200 dark:bg-slate-800 rounded-2xl w-full" />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="h-28 bg-slate-200 dark:bg-slate-800 rounded-2xl" />
                <div className="h-28 bg-slate-200 dark:bg-slate-800 rounded-2xl" />
                <div className="h-28 bg-slate-200 dark:bg-slate-800 rounded-2xl" />
              </div>
              <div className="h-64 bg-slate-200 dark:bg-slate-800 rounded-2xl w-full" />
            </div>
          )}

          {/* Active Tab View */}
          {!loading && analysis && (
            <>
              {activeTab === 'overview' && (
                <HealthScoreGauge
                  healthScore={analysis.health_score}
                  cashflow={analysis.cashflow}
                  debt={analysis.debt}
                  emergency={analysis.emergency}
                  t={t}
                />
              )}

              {activeTab === 'savings' && (
                <SavingsView
                  cashflow={analysis.cashflow}
                  emergency={analysis.emergency}
                  t={t}
                />
              )}

              {activeTab === 'debt' && (
                <DebtView debt={analysis.debt} t={t} />
              )}

              {activeTab === 'goals' && (
                <GoalsView
                  goalsData={analysis.goals}
                  savingsCapacity={analysis.cashflow?.savings_capacity}
                  t={t}
                />
              )}

              {activeTab === 'allocation' && (
                <AllocationView allocation={analysis.allocation} t={t} />
              )}

              {activeTab === 'retirement' && (
                <RetirementView retirement={analysis.retirement} t={t} />
              )}

              {activeTab === 'checklist' && (
                <ActionPlanView actionPlan={analysis.action_plan} t={t} />
              )}

              {activeTab === 'whatif' && (
                <WhatIfSimulator
                  profile={profile}
                  initialAnalysis={analysis}
                  t={t}
                />
              )}

              {activeTab === 'chat' && (
                <CoachChat
                  language={language}
                  setLanguage={setLanguage}
                  t={t}
                />
              )}
            </>
          )}

          {/* Bottom Regulatory Disclaimer on Every Page */}
          <div className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-800 text-center">
            <p className="text-xs text-slate-400 dark:text-slate-500 max-w-2xl mx-auto leading-relaxed">
              <strong>Regulatory Notice:</strong> This is educational guidance, not registered investment advice. Please consult a SEBI-registered advisor before investing. Data remains on your local device/instance and is never shared.
            </p>
          </div>
        </main>
      </div>

      {/* Modals */}
      <ProfileFormModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        initialProfile={profile}
        onSave={handleSaveProfile}
        t={t}
      />

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={(usr) => setCurrentUser(usr)}
        t={t}
      />
    </div>
  );
}
