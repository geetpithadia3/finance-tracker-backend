-- Sample data for budget plans and periods
-- This script provides example data to test the budget system

-- Note: Replace the UUIDs below with actual user_id and category_id values from your database

-- Sample Budget Plans
INSERT INTO budget_plans (
    id, user_id, category_id, name, type, start_date, end_date, 
    recurrence, rollover_policy, max_amount, alert_thresholds, tags, is_archived
) VALUES 
-- Regular monthly groceries budget
(
    'bp-grocery-001', 
    'user-123-456', 
    'cat-groceries-001', 
    'Monthly Groceries', 
    'REGULAR', 
    '2024-01-01 00:00:00', 
    NULL,
    'MONTHLY', 
    'REMAINING', 
    500.00, 
    '[80, 100]', 
    '[]', 
    FALSE
),

-- Temporary vacation budget
(
    'bp-vacation-001', 
    'user-123-456', 
    'cat-travel-001', 
    'Europe Trip 2024', 
    'TEMPORARY', 
    '2024-06-01 00:00:00', 
    '2024-06-30 23:59:59',
    'NONE', 
    'NONE', 
    3000.00, 
    '[75, 90, 100]', 
    '["vacation", "europe", "travel"]', 
    FALSE
),

-- Quarterly entertainment budget with rollover
(
    'bp-entertainment-001', 
    'user-123-456', 
    'cat-entertainment-001', 
    'Quarterly Entertainment', 
    'REGULAR', 
    '2024-01-01 00:00:00', 
    NULL,
    'QUARTERLY', 
    'BOTH', 
    600.00, 
    '[80, 100]', 
    '["entertainment", "fun"]', 
    FALSE
);

-- Sample Budget Periods
INSERT INTO budget_periods (
    id, plan_id, period_start, period_end, allocated, spent, carried_over
) VALUES 
-- January 2024 groceries period
(
    'period-grocery-jan-2024', 
    'bp-grocery-001', 
    '2024-01-01 00:00:00', 
    '2024-01-31 23:59:59', 
    500.00, 
    425.50, 
    0.00
),

-- February 2024 groceries period (with rollover from January)
(
    'period-grocery-feb-2024', 
    'bp-grocery-001', 
    '2024-02-01 00:00:00', 
    '2024-02-29 23:59:59', 
    574.50, 
    480.25, 
    74.50
),

-- March 2024 groceries period (current)
(
    'period-grocery-mar-2024', 
    'bp-grocery-001', 
    '2024-03-01 00:00:00', 
    '2024-03-31 23:59:59', 
    594.25, 
    320.75, 
    94.25
),

-- Vacation budget period (temporary)
(
    'period-vacation-jun-2024', 
    'bp-vacation-001', 
    '2024-06-01 00:00:00', 
    '2024-06-30 23:59:59', 
    3000.00, 
    2750.00, 
    0.00
),

-- Q1 2024 entertainment period
(
    'period-entertainment-q1-2024', 
    'bp-entertainment-001', 
    '2024-01-01 00:00:00', 
    '2024-03-31 23:59:59', 
    600.00, 
    480.00, 
    0.00
),

-- Q2 2024 entertainment period (with rollover)
(
    'period-entertainment-q2-2024', 
    'bp-entertainment-001', 
    '2024-04-01 00:00:00', 
    '2024-06-30 23:59:59', 
    720.00, 
    150.00, 
    120.00
);

-- Verification queries to check the sample data
-- Uncomment these to verify the data was inserted correctly

/*
-- Check budget plans
SELECT 
    bp.name,
    bp.type,
    bp.recurrence,
    bp.rollover_policy,
    bp.max_amount,
    COUNT(periods.id) as period_count
FROM budget_plans bp
LEFT JOIN budget_periods periods ON bp.id = periods.plan_id
GROUP BY bp.id, bp.name, bp.type, bp.recurrence, bp.rollover_policy, bp.max_amount
ORDER BY bp.created_at;

-- Check budget periods with calculated status
SELECT 
    bp.name as budget_name,
    per.period_start,
    per.period_end,
    per.allocated,
    per.spent,
    per.carried_over,
    ROUND((per.spent / per.allocated * 100), 2) as percentage_used,
    CASE 
        WHEN per.spent / per.allocated >= 1.0 THEN 'Over Budget'
        WHEN per.spent / per.allocated >= 0.8 THEN 'Near Limit'
        ELSE 'Under Budget'
    END as status
FROM budget_periods per
JOIN budget_plans bp ON per.plan_id = bp.id
ORDER BY bp.name, per.period_start;
*/