"""Set or clear a demo service's fault toggles from inside its own pod.

    kubectl -n aiops-estate exec deploy/pacs -- python -m aiops_sim.admin set volume_used_percent=96
    kubectl -n aiops-estate exec deploy/pacs -- python -m aiops_sim.admin clear

Calls 127.0.0.1 with the pod's own AIOPS_ESTATE_ADMIN_TOKEN, so the admin
endpoint never has to be reachable over the network.
"""

import os
import sys

import httpx

URL = "http://127.0.0.1:8080/admin/faults"


def main(argv: list[str], transport: httpx.BaseTransport | None = None) -> int:
    headers = {"Authorization": f"Bearer {os.environ.get('AIOPS_ESTATE_ADMIN_TOKEN', '')}"}
    with httpx.Client(timeout=5.0, headers=headers, transport=transport) as client:
        if argv[:1] == ["clear"]:
            response = client.delete(URL)
        elif argv[:1] == ["set"] and len(argv) > 1:
            current = client.get(URL)
            current.raise_for_status()
            changes = dict(arg.split("=", 1) for arg in argv[1:])
            response = client.put(URL, json={**current.json(), **changes})
        else:
            print("usage: python -m aiops_sim.admin set key=value ... | clear", file=sys.stderr)
            return 2
    print(response.status_code, response.text)
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
