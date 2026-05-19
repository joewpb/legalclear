-- Phase 1: add LLM cost columns to usage_stats

alter table public.usage_stats
  add column if not exists total_input_tokens  int,
  add column if not exists total_output_tokens int,
  add column if not exists estimated_cost_usd  numeric;
