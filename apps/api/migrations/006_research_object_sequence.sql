-- Migration 006: persist the parsed nucleotide sequence on research objects.
-- Run once in the Supabase SQL editor.
--
-- research_objects stored only derived summaries of an upload (sequence_length,
-- gc_content, fasta_preview) but never the sequence itself. The base-edit
-- pipeline needs the actual bases: without them create_run() halts at `input`
-- with an `input_invalid` provenance event, so no run could ever reach the
-- engine. This adds the column the pipeline reads.
--
-- Nullable on purpose: research objects created before this migration (and any
-- created without a FASTA upload) have no sequence, and the pipeline already
-- handles that case by failing honestly at the input stage rather than
-- fabricating a result.

ALTER TABLE public.research_objects
  ADD COLUMN IF NOT EXISTS sequence TEXT;
