from __future__ import annotations

import asyncio
import os
import tempfile

from copilot import CopilotClient


async def main() -> int:
    configured = os.environ.get("COPILOT_MODEL", "gpt-5.4")
    if not os.environ.get("COPILOT_GITHUB_TOKEN"):
        raise SystemExit(
            "COPILOT_GITHUB_TOKEN is required for the live challenge in this personal repository. "
            "Store a fine-grained user PAT with Account > Copilot Requests: write as the Actions repository secret COPILOT_GITHUB_TOKEN."
        )
    with tempfile.TemporaryDirectory(prefix="cepio-copilot-preflight-") as base_directory:
        # Do not pass github_token explicitly: the Copilot SDK intentionally resolves
        # COPILOT_GITHUB_TOKEN before GH_TOKEN/GITHUB_TOKEN for user-authenticated automation.
        async with CopilotClient(mode="empty", base_directory=base_directory) as client:
            models = await asyncio.wait_for(client.list_models(), timeout=20.0)
            ids = [str(getattr(model, "id", "")) for model in models]
            print("CEPIO_COPILOT_PREFLIGHT models=" + ",".join(ids))
            print(f"CEPIO_COPILOT_PREFLIGHT configured={configured} available={configured in ids}")
            if configured not in ids:
                raise SystemExit(f"Configured Copilot model is unavailable: {configured}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
