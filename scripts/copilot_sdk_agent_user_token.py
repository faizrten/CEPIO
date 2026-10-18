from __future__ import annotations

import os
import runpy


def main() -> None:
    token = os.environ.get("COPILOT_GITHUB_TOKEN")
    if not token:
        raise SystemExit(
            "COPILOT_GITHUB_TOKEN is required. Add the fine-grained user PAT as a GitHub Actions repository secret."
        )
    # The underlying adapter passes github_token explicitly. Mirror the documented
    # user PAT into GITHUB_TOKEN only inside this child process so the SDK receives
    # the user-scoped Copilot entitlement rather than the Actions installation token.
    os.environ["GITHUB_TOKEN"] = token
    runpy.run_path("scripts/copilot_sdk_agent.py", run_name="__main__")


if __name__ == "__main__":
    main()
