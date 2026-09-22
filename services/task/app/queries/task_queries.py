SELECT_HEALTH_CHECK = "SELECT 1"

SELECT_TASKS = """
    SELECT
        t.id,
        t.user_id,
        t.title,
        t.description,
        t.status,
        t.last_updated_by,
        t.created_at,
        t.updated_at,
        COALESCE(
            ARRAY_AGG(ts.user_id) FILTER (WHERE ts.user_id IS NOT NULL),
            ARRAY[]::BIGINT[]
        ) AS shared_with
    FROM tasks AS t
    LEFT JOIN task_shares AS ts
        ON ts.task_id = t.id
    GROUP BY t.id
    ORDER BY t.id
"""

SELECT_USER_BY_ID = "SELECT 1 FROM users WHERE id = %s"

SELECT_EXISTING_USER_IDS = "SELECT id FROM users WHERE id = ANY(%s)"

INSERT_TASK = """
    INSERT INTO tasks (user_id, title, description, status, last_updated_by)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
"""

INSERT_TASK_SHARE = """
    INSERT INTO task_shares (task_id, user_id)
    VALUES (%s, %s)
    ON CONFLICT (task_id, user_id) DO NOTHING
"""

SELECT_TASK_WITH_SHARES = """
    SELECT
        t.id,
        t.user_id,
        t.title,
        t.description,
        t.status,
        t.last_updated_by,
        t.created_at,
        t.updated_at,
        COALESCE(
            ARRAY_AGG(ts.user_id) FILTER (WHERE ts.user_id IS NOT NULL),
            ARRAY[]::BIGINT[]
        ) AS shared_with
    FROM tasks AS t
    LEFT JOIN task_shares AS ts
        ON ts.task_id = t.id
    WHERE t.id = %s
    GROUP BY t.id
"""

UPDATE_TASK = """
    UPDATE tasks
    SET
        title = COALESCE(%s, title),
        description = COALESCE(%s, description),
        status = COALESCE(%s, status),
        last_updated_by = %s,
        updated_at = now()
    WHERE id = %s
    RETURNING id
"""
