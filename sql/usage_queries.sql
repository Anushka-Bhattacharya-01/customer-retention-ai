-- Basic Postgres queries on the assistant's tables.
-- Run with: psql "$DATABASE_URL" -f sql/usage_queries.sql

-- 1. Cost and tokens per day
SELECT DATE(created_at)  AS day,
       COUNT(*)          AS llm_calls,
       SUM(input_tokens) AS input_tokens,
       SUM(output_tokens) AS output_tokens,
       SUM(cost_usd)     AS cost_usd
FROM llm_usage
GROUP BY DATE(created_at)
ORDER BY day DESC;

-- 2. Top 10 most expensive conversations
SELECT c.id, c.question, SUM(u.cost_usd) AS cost_usd
FROM conversations c
JOIN llm_usage u ON u.conversation_id = c.id
GROUP BY c.id, c.question
ORDER BY cost_usd DESC
LIMIT 10;

-- 3. Success vs error count
SELECT status, COUNT(*) AS requests
FROM conversations
GROUP BY status;

-- 4. Latest failed conversations (for incident notes)
SELECT id, created_at, question, answer
FROM conversations
WHERE status = 'error'
ORDER BY created_at DESC
LIMIT 20;
