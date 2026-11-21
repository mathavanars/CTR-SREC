-- 0007_views_and_rpc.sql
-- Views and RPCs for ArthMitra dashboard aggregates
-- ------------------------------------------------------------

-- Enable extension for statistical functions if needed
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- View: income_vs_expense_last_n_months
-- Returns month, total_income, total_expense for the last N months (default 12)
-- Income is taken from financial_profiles.monthly_income (assumed constant per month)
-- Expense is summed across expense columns in expense_analysis
CREATE OR REPLACE VIEW public.income_vs_expense_last_n_months AS
SELECT
    ea.user_id,
    ea.period_month AS month,
    fp.monthly_income AS total_income,
    (ea.food + ea.travel + ea.shopping + ea.bills + ea.entertainment + ea.healthcare + ea.other) AS total_expense
FROM public.expense_analysis ea
JOIN public.financial_profiles fp ON fp.user_id = ea.user_id
SELECT
    ea.period_month AS month,
    fp.monthly_income AS total_income,
    (ea.food + ea.travel + ea.shopping + ea.bills + ea.entertainment + ea.healthcare + ea.other) AS total_expense
FROM public.expense_analysis ea
JOIN public.financial_profiles fp ON fp.user_id = ea.user_id
WHERE ea.user_id = (SELECT auth.uid())
ORDER BY ea.period_month DESC;

-- View: savings_growth
-- Calculates monthly savings as income minus total expense per user
CREATE OR REPLACE VIEW public.savings_growth AS
SELECT
    ea.period_month AS month,
    fp.user_id,
    fp.monthly_income - (ea.food + ea.travel + ea.shopping + ea.bills + ea.entertainment + ea.healthcare + ea.other) AS total_savings
FROM public.expense_analysis ea
JOIN public.financial_profiles fp ON fp.user_id = ea.user_id
WHERE ea.user_id = (SELECT auth.uid());

-- Shows each goal with current progress percentage and status
CREATE OR REPLACE VIEW public.goal_progress_summary AS
SELECT
    g.id,
    g.user_id,
    g.goal_name,
    g.goal_type,
    g.target_amount,
    g.current_amount,
    ROUND((g.current_amount / NULLIF(g.target_amount,0)) * 100, 2) AS progress_pct,
    g.status,
    g.priority
FROM public.goals g;

-- View: health_score_latest
-- Latest health score per user per category
CREATE OR REPLACE VIEW public.health_score_latest AS
SELECT DISTINCT ON (user_id, category)
    hs.id,
    hs.user_id,
    hs.category,
    hs.score,
    hs.factors,
    hs.calculated_at
FROM public.health_scores hs
ORDER BY user_id, category, calculated_at DESC;

-- RPC: get_dashboard_summary(user_uuid uuid)
-- Returns aggregated data for dashboard widgets for a single user
CREATE OR REPLACE FUNCTION public.get_dashboard_summary(p_user_id uuid)
RETURNS TABLE(
    income_vs_expense jsonb,
    savings_growth jsonb,
    goal_progress jsonb,
    health_score jsonb
) LANGUAGE plpgsql SECURITY INVOKER AS $$
BEGIN
    RETURN QUERY SELECT
        (SELECT jsonb_agg(row_to_json(t)) FROM (
            SELECT month, total_income, total_expense
            FROM public.income_vs_expense_last_n_months
            WHERE month >= date_trunc('month', now()) - interval '11 months'
            ORDER BY month
        ) t) AS income_vs_expense,
        (SELECT jsonb_agg(row_to_json(t)) FROM (
            SELECT period_month AS month, total_savings
            FROM public.savings_growth
            WHERE user_id = p_user_id
            ORDER BY period_month
        ) t) AS savings_growth,
        (SELECT jsonb_agg(row_to_json(t)) FROM (
            SELECT * FROM public.goal_progress_summary WHERE user_id = p_user_id
        ) t) AS goal_progress,
        (SELECT jsonb_agg(row_to_json(t)) FROM (
            SELECT * FROM public.health_score_latest WHERE user_id = p_user_id
        ) t) AS health_score;
END;
$$;

-- RPC: get_income_vs_expense(p_user_id uuid, p_months int)
CREATE OR REPLACE FUNCTION public.get_income_vs_expense(p_user_id uuid, p_months int DEFAULT 12)
RETURNS TABLE(month date, total_income numeric, total_expense numeric)
LANGUAGE sql SECURITY INVOKER AS $$
    SELECT month, total_income, total_expense
    FROM public.income_vs_expense_last_n_months
    WHERE month >= date_trunc('month', now()) - (p_months-1) * interval '1 month'
    ORDER BY month;
$$;

-- RPC: get_goal_progress(p_user_id uuid)
CREATE OR REPLACE FUNCTION public.get_goal_progress(p_user_id uuid)
RETURNS TABLE(id uuid, goal_name text, progress_pct numeric, status text, priority int)
LANGUAGE sql SECURITY INVOKER AS $$
    SELECT id, goal_name, progress_pct, status, priority
    FROM public.goal_progress_summary
    WHERE user_id = p_user_id
    ORDER BY priority DESC;
$$;

-- RPC: get_latest_health_scores(p_user_id uuid)
CREATE OR REPLACE FUNCTION public.get_latest_health_scores(p_user_id uuid)
RETURNS TABLE(category text, score int, calculated_at timestamptz)
LANGUAGE sql SECURITY INVOKER AS $$
    SELECT category, score, calculated_at
    FROM public.health_score_latest
    WHERE user_id = p_user_id;
$$;

-- Revoke public privileges and grant to authenticated role
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_dashboard_summary(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_income_vs_expense(uuid, int) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_goal_progress(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_latest_health_scores(uuid) TO authenticated;

-- Rollback section (for Supabase migrations)
-- DROP VIEW IF EXISTS public.income_vs_expense_last_n_months;
-- DROP VIEW IF EXISTS public.goal_progress_summary;
-- DROP VIEW IF EXISTS public.health_score_latest;
-- DROP FUNCTION IF EXISTS public.get_dashboard_summary(uuid);
-- DROP FUNCTION IF EXISTS public.get_income_vs_expense(uuid, int);
-- DROP FUNCTION IF EXISTS public.get_goal_progress(uuid);
-- DROP FUNCTION IF EXISTS public.get_latest_health_scores(uuid);
