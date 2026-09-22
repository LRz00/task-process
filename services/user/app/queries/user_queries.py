SELECT_HEALTH_CHECK = "SELECT 1"

CREATE_USER_GROUP_TABLE = """
    CREATE TABLE IF NOT EXISTS user_groups (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
"""

CREATE_USER_GROUP_MEMBERS_TABLE = """
    CREATE TABLE IF NOT EXISTS user_group_members (
        group_id BIGINT NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL REFERENCES users(id),
        PRIMARY KEY (group_id, user_id)
    )
"""

SELECT_USERS = """
    SELECT id, name, email, created_at, updated_at
    FROM users
    ORDER BY id
"""

INSERT_USER = """
    INSERT INTO users (name, email)
    VALUES (%s, %s)
    RETURNING id, name, email, created_at, updated_at
"""

SELECT_USER_TASKS = """
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
            ARRAY_AGG(ts_all.user_id) FILTER (WHERE ts_all.user_id IS NOT NULL),
            ARRAY[]::BIGINT[]
        ) AS shared_with
    FROM tasks AS t
    LEFT JOIN task_shares AS ts_all
        ON ts_all.task_id = t.id
    WHERE t.user_id = %s
       OR EXISTS (
           SELECT 1
           FROM task_shares AS ts_user
           WHERE ts_user.task_id = t.id
             AND ts_user.user_id = %s
       )
    GROUP BY t.id
    ORDER BY t.id
"""

SELECT_USER_BY_ID = "SELECT 1 FROM users WHERE id = %s"

SELECT_EXISTING_USER_IDS = "SELECT id FROM users WHERE id = ANY(%s)"

INSERT_USER_GROUP = "INSERT INTO user_groups DEFAULT VALUES RETURNING id"

INSERT_USER_GROUP_MEMBERS = """
    INSERT INTO user_group_members (group_id, user_id)
    VALUES (%s, %s)
"""
