-- Only counts and hashes are emitted; no original user values.
SELECT format('SELECT %L, count(*), md5(coalesce(string_agg(row_hash, '''' ORDER BY row_hash), '''')) FROM (SELECT md5(row_to_json(t)::text) AS row_hash FROM public.%I t) q;', tablename, tablename)
FROM pg_tables WHERE schemaname='public' ORDER BY tablename
\gexec
