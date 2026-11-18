"""Steady synthetic traffic for the estate. Run: python -m aiops_sim.loadgen

Env: RATE_PER_SECOND (default 2), PEER_URL_PATTERN (default http://{id}:8080).
Scenario S6's login surge raises RATE_PER_SECOND through a rollout.
"""

import asyncio
import itertools
import os

import httpx

ENTRY_POINTS = ("patient-portal", "ehr-api", "lis", "pacs")
ROUTED = ("lis", "pacs", "ehr-api")


async def run(rate: float, url_pattern: str) -> None:
    targets = itertools.cycle(ENTRY_POINTS)
    destinations = itertools.cycle(ROUTED)
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            target = next(targets)
            try:
                await client.get(f"{url_pattern.format(id=target)}/work")
                await client.post(
                    f"{url_pattern.format(id='interface-engine')}/messages",
                    json={"destination": next(destinations)},
                )
            except httpx.HTTPError:
                pass  # the estate being unhealthy is the point; keep going
            await asyncio.sleep(1 / rate)


if __name__ == "__main__":
    asyncio.run(
        run(
            float(os.environ.get("RATE_PER_SECOND", "2")),
            os.environ.get("PEER_URL_PATTERN", "http://{id}:8080"),
        )
    )
