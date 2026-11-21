-- 0008_seed_dev_data.sql
-- Seed data for development environment
-- ------------------------------------------------------------

-- Define a deterministic UUID for the test user (replace with real auth user in prod)
DO $$
DECLARE
    test_user_uuid uuid := '11111111-1111-1111-1111-111111111111';
BEGIN
    -- Insert into the auth.users table is normally done via Supabase Auth API.
    -- For local dev we can insert a placeholder row into the public.users_profile and related tables.
    INSERT INTO public.users_profile (id, email, full_name, avatar_url, phone, preferred_currency, theme_preference, onboarding_completed, created_at, updated_at)
    VALUES (
        test_user_uuid,
        'testuser@example.com',
        'Test User',
        NULL,
        NULL,
        'INR',
        'light',
        FALSE,
        now(),
        now()
    ) ON CONFLICT (id) DO UPDATE SET updated_at = now();

    INSERT INTO public.financial_profiles (user_id, monthly_income, fixed_expenses, variable_expenses, total_savings, total_investments, total_liabilities, dependents, age, risk_appetite, risk_score, financial_score, emergency_fund_target_months, created_at, updated_at)
    VALUES (
        test_user_uuid,
        120000.00,
        30000.00,
        15000.00,
        500000.00,
        200000.00,
        100000.00,
        2,
        30,
        'moderate',
        70,
        75,
        6,
        now(),
        now()
    ) ON CONFLICT (user_id) DO UPDATE SET updated_at = now();

    -- Sample goals
    INSERT INTO public.goals (id, user_id, goal_name, goal_type, target_amount, current_amount, target_date, monthly_contribution, priority, status, created_at, updated_at)
    VALUES
        (gen_random_uuid(), test_user_uuid, 'Emergency Fund', 'emergency_fund', 600000.00, 250000.00, (now() + interval '12 months')::date, 50000.00, 5, 'active', now(), now()),
        (gen_random_uuid(), test_user_uuid, 'Retirement Corpus', 'retirement', 3000000.00, 800000.00, (now() + interval '240 months')::date, 150000.00, 4, 'active', now(), now());

    -- Sample loans
    INSERT INTO public.loans (id, user_id, loan_type, lender_name, principal_amount, outstanding_amount, interest_rate, emi_amount, tenure_months_remaining, priority, status, start_date, created_at, updated_at)
    VALUES
        (gen_random_uuid(), test_user_uuid, 'home', 'Bank A', 5000000.00, 3500000.00, 7.5, 35000.00, 180, 3, 'active', (now() - interval '5 years')::date, now(), now()),
        (gen_random_uuid(), test_user_uuid, 'car', 'Bank B', 800000.00, 400000.00, 9.2, 15000.00, 48, 2, 'active', (now() - interval '1 year')::date, now(), now());

    -- Sample investments
    INSERT INTO public.investments (id, user_id, category, allocation_percentage, invested_amount, current_value, created_at, updated_at)
    VALUES
        (gen_random_uuid(), test_user_uuid, 'fd', 30.00, 200000.00, 210000.00, now(), now()),
        (gen_random_uuid(), test_user_uuid, 'sip_mutual_fund', 40.00, 300000.00, 320000.00, now(), now()),
        (gen_random_uuid(), test_user_uuid, 'gold', 15.00, 100000.00, 110000.00, now(), now()),
        (gen_random_uuid(), test_user_uuid, 'nps', 15.00, 150000.00, 155000.00, now(), now());

    -- Sample expense analysis for last 6 months
    INSERT INTO public.expense_analysis (id, user_id, period_month, food, travel, shopping, bills, entertainment, healthcare, other)
    SELECT
        gen_random_uuid(),
        test_user_uuid,
        date_trunc('month', now()) - (interval '1 month' * generate_series(0,5))::date,
        (random()*20000)::numeric(14,2) AS food,
        (random()*5000)::numeric(14,2) AS travel,
        (random()*8000)::numeric(14,2) AS shopping,
        (random()*7000)::numeric(14,2) AS bills,
        (random()*4000)::numeric(14,2) AS entertainment,
        (random()*3000)::numeric(14,2) AS healthcare,
        (random()*2000)::numeric(14,2) AS other;

    -- Sample health scores (latest only)
    INSERT INTO public.health_scores (id, user_id, score, category, factors, calculated_at)
    VALUES
        (gen_random_uuid(), test_user_uuid, 78, 'overall', '{"savings":75,"debt":80,"investments":70}'::jsonb, now()),
        (gen_random_uuid(), test_user_uuid, 80, 'savings', '{"savings_rate":70}'::jsonb, now()),
        (gen_random_uuid(), test_user_uuid, 65, 'debt', '{"debt_to_income":45}'::jsonb, now());
END $$;

-- Rollback (delete seeded data)
-- DELETE FROM public.health_scores WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.expense_analysis WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.investments WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.loans WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.goals WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.financial_profiles WHERE user_id = '11111111-1111-1111-1111-111111111111';
-- DELETE FROM public.users_profile WHERE id = '11111111-1111-1111-1111-111111111111';
