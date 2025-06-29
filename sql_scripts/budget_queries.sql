-- Useful queries for budget management and reporting
-- These queries can be used for administration, reporting, and debugging

-- 1. Get all active budgets for a user with current period status
SELECT 
    bp.id as budget_id,
    bp.name as budget_name,
    bp.type,
    bp.recurrence,
    bp.max_amount,
    c.name as category_name,
    per.period_start,
    per.period_end,
    per.allocated,
    per.spent,
    per.carried_over,
    (per.allocated - per.spent) as remaining,
    ROUND((per.spent / per.allocated * 100), 2) as percentage_used,
    CASE 
        WHEN per.spent / per.allocated >= 1.0 THEN 'over_budget'
        WHEN per.spent / per.allocated >= 0.8 THEN 'near_limit'
        ELSE 'under_budget'
    END as status
FROM budget_plans bp
JOIN categories c ON bp.category_id = c.id
LEFT JOIN budget_periods per ON bp.id = per.plan_id 
    AND per.period_start <= CURRENT_TIMESTAMP 
    AND per.period_end >= CURRENT_TIMESTAMP
WHERE bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND bp.is_archived = FALSE
ORDER BY bp.created_at DESC;

-- 2. Get budget alerts (budgets exceeding thresholds)
SELECT 
    bp.id as budget_id,
    bp.name as budget_name,
    c.name as category_name,
    per.allocated,
    per.spent,
    ROUND((per.spent / per.allocated * 100), 2) as percentage_used,
    bp.alert_thresholds,
    CASE 
        WHEN per.spent / per.allocated >= 1.0 THEN 'exceeded'
        WHEN per.spent / per.allocated >= 0.8 THEN 'warning'
        ELSE 'info'
    END as alert_type
FROM budget_plans bp
JOIN categories c ON bp.category_id = c.id
JOIN budget_periods per ON bp.id = per.plan_id 
    AND per.period_start <= CURRENT_TIMESTAMP 
    AND per.period_end >= CURRENT_TIMESTAMP
WHERE bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND bp.is_archived = FALSE
    AND per.allocated > 0
    AND (per.spent / per.allocated) >= 0.8  -- Only show budgets at 80% or higher
ORDER BY percentage_used DESC;

-- 3. Budget summary by category for a specific month
SELECT 
    c.name as category_name,
    COUNT(bp.id) as budget_count,
    SUM(per.allocated) as total_allocated,
    SUM(per.spent) as total_spent,
    SUM(per.allocated - per.spent) as total_remaining,
    ROUND(AVG(per.spent / per.allocated * 100), 2) as avg_percentage_used
FROM categories c
LEFT JOIN budget_plans bp ON c.id = bp.category_id 
    AND bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND bp.is_archived = FALSE
LEFT JOIN budget_periods per ON bp.id = per.plan_id 
    AND per.period_start <= '2024-03-31 23:59:59'  -- Replace with target month end
    AND per.period_end >= '2024-03-01 00:00:00'    -- Replace with target month start
WHERE c.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND c.is_active = TRUE
GROUP BY c.id, c.name
HAVING budget_count > 0
ORDER BY total_allocated DESC;

-- 4. Historical budget performance (last 6 months)
SELECT 
    bp.name as budget_name,
    per.period_start,
    per.period_end,
    per.allocated,
    per.spent,
    per.carried_over,
    ROUND((per.spent / per.allocated * 100), 2) as percentage_used,
    CASE 
        WHEN per.spent <= per.allocated THEN 'success'
        WHEN per.spent <= per.allocated * 1.1 THEN 'warning'
        ELSE 'danger'
    END as performance
FROM budget_plans bp
JOIN budget_periods per ON bp.id = per.plan_id
WHERE bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND per.period_start >= DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 6 MONTH)
    AND bp.is_archived = FALSE
ORDER BY bp.name, per.period_start DESC;

-- 5. Find budgets that need new periods (for recurring budgets)
SELECT 
    bp.id as budget_id,
    bp.name as budget_name,
    bp.recurrence,
    MAX(per.period_end) as last_period_end,
    CASE bp.recurrence
        WHEN 'MONTHLY' THEN DATE_ADD(MAX(per.period_end), INTERVAL 1 DAY)
        WHEN 'QUARTERLY' THEN DATE_ADD(MAX(per.period_end), INTERVAL 1 DAY)
        ELSE NULL
    END as next_period_start
FROM budget_plans bp
LEFT JOIN budget_periods per ON bp.id = per.plan_id
WHERE bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND bp.is_archived = FALSE
    AND bp.recurrence IN ('MONTHLY', 'QUARTERLY')
    AND (bp.end_date IS NULL OR bp.end_date >= CURRENT_TIMESTAMP)
GROUP BY bp.id, bp.name, bp.recurrence
HAVING MAX(per.period_end) < CURRENT_TIMESTAMP
    OR MAX(per.period_end) IS NULL
ORDER BY last_period_end;

-- 6. Calculate total spending vs budgets for a user
SELECT 
    'Total' as summary_type,
    COUNT(DISTINCT bp.id) as active_budgets,
    SUM(per.allocated) as total_budgeted,
    SUM(per.spent) as total_spent,
    SUM(per.allocated - per.spent) as total_remaining,
    ROUND((SUM(per.spent) / SUM(per.allocated) * 100), 2) as overall_percentage
FROM budget_plans bp
JOIN budget_periods per ON bp.id = per.plan_id 
    AND per.period_start <= CURRENT_TIMESTAMP 
    AND per.period_end >= CURRENT_TIMESTAMP
WHERE bp.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND bp.is_archived = FALSE;

-- 7. Transactions affecting budget spending for a specific period
SELECT 
    t.id as transaction_id,
    t.description,
    t.amount,
    t.occurred_on,
    c.name as category_name,
    bp.name as budget_name,
    per.period_start,
    per.period_end
FROM transactions t
JOIN categories c ON t.category_id = c.id
JOIN budget_plans bp ON c.id = bp.category_id
JOIN budget_periods per ON bp.id = per.plan_id
WHERE t.user_id = 'USER_ID_HERE'  -- Replace with actual user ID
    AND t.type = 'EXPENSE'
    AND t.is_deleted = FALSE
    AND t.occurred_on >= per.period_start
    AND t.occurred_on <= per.period_end
    AND bp.is_archived = FALSE
    AND per.id = 'PERIOD_ID_HERE'  -- Replace with specific period ID
ORDER BY t.occurred_on DESC;

-- 8. Clean up archived budgets and old periods (maintenance query)
-- Use with caution - this will permanently delete data
/*
DELETE FROM budget_periods 
WHERE plan_id IN (
    SELECT id FROM budget_plans 
    WHERE is_archived = TRUE 
    AND updated_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 YEAR)
);

DELETE FROM budget_plans 
WHERE is_archived = TRUE 
AND updated_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 YEAR);
*/