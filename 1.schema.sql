CREATE TABLE IF NOT EXISTS members (
    member_id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    jkt48_member_type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS shows (
    schedule_id INT PRIMARY KEY,
    reference_code VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    show_date TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS show_members (
    schedule_id INT REFERENCES shows(schedule_id) ON DELETE CASCADE,
    member_id INT REFERENCES members(member_id) ON DELETE CASCADE,
    PRIMARY KEY (schedule_id, member_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id SERIAL PRIMARY KEY,
    schedule_id INT UNIQUE REFERENCES shows(schedule_id) ON DELETE CASCADE,
    attended_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);