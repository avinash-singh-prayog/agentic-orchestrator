import asyncio
from psycopg import AsyncConnection
import os

# You may need to set DATABASE_URL env var if not set in shell
# Assuming the default from docker-compose or similar if local
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/agentic_orchestrator")

async def dump_tables():
    print(f"Connecting to {DATABASE_URL}")
    try:
        async with await AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                print("\n--- Users ---")
                await cur.execute("SELECT id, email, tenant_id FROM users")
                async for row in cur:
                    print(row)
                
                print("\n--- User LLM Configs ---")
                await cur.execute("SELECT id, user_id, provider, model_name, is_active, config_name FROM user_llm_configs")
                async for row in cur:
                    print(row)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(dump_tables())
