-- 1. Create the read-only user
CREATE USER readonly_recruiter WITH PASSWORD 'temp_30_day_token_123';

-- 2. Grant connection access to the database
GRANT CONNECT ON DATABASE postgres TO readonly_recruiter;

-- 3. Grant usage on the public schema (where the tables and functions are)
GRANT USAGE ON SCHEMA public TO readonly_recruiter;

-- 4. Grant SELECT permission ONLY on the necessary tables
GRANT SELECT ON public.document_chunks TO readonly_recruiter;
GRANT SELECT ON public.documents TO readonly_recruiter;

-- 5. Grant EXECUTE permission on the hybrid search function
GRANT EXECUTE ON FUNCTION public.match_document_chunks_hybrid(text, vector, int, jsonb) TO readonly_recruiter;

-- 6. Ensure future tables don't accidentally get exposed
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM readonly_recruiter;
