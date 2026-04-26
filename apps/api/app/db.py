# Supabase client factory. Import get_supabase() wherever DB access is needed.
# Uses the service role key — never expose this key to the frontend.

from supabase import Client, create_client

from app.core.config import settings


def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)
