CREATE DATABASE epic_ai_reads;

CREATE USER epic_ai_reads_user WITH PASSWORD 'change_this_password';

GRANT ALL PRIVILEGES ON DATABASE epic_ai_reads TO epic_ai_reads_user;

-- After creating the database, set:
-- DATABASE_URL=postgresql://epic_ai_reads_user:change_this_password@127.0.0.1:5432/epic_ai_reads
-- Then run:
-- python manage.py migrate
