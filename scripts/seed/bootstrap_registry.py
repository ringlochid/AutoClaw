import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.session import get_session_factory
from app.services.registry_service import bootstrap_registry


async def main() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await bootstrap_registry(session, publish=True)
        await session.commit()
    print("bootstrapped registry:", result)


if __name__ == "__main__":
    asyncio.run(main())
