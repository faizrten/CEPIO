# NVIDIA cuGraph acceleration for CEPIO

CEPIO graph intelligence is backend-neutral. The canonical CEPIO graph contract is built with NetworkX semantics and can optionally dispatch supported algorithms to NVIDIA RAPIDS `nx-cugraph` when the deployment has a compatible NVIDIA GPU runtime.

This keeps CEPIO portable and Microsoft-native while allowing GPU acceleration in AKS or other Linux GPU deployments.

## What is accelerated

The first integration exposes:

- PageRank centrality;
- degree centrality;
- betweenness centrality;
- eigenvector centrality;
- Louvain community detection;
- dependency blast-radius traversal.

The public CEPIO API does not change when acceleration is enabled.

## Backend selection

Use `CEPIO_GRAPH_BACKEND`:

```bash
# Default: attempt cuGraph if installed, otherwise use NetworkX
export CEPIO_GRAPH_BACKEND=auto

# Force CPU/reference behavior
export CEPIO_GRAPH_BACKEND=networkx

# Require GPU execution; fail closed if cuGraph cannot run
export CEPIO_GRAPH_BACKEND=cugraph
```

`auto` is recommended for portable deployments. `cugraph` is recommended only for a deployment profile that guarantees the required RAPIDS/CUDA runtime.

## Installing nx-cugraph

CEPIO does not install CUDA/RAPIDS packages as a core dependency because CPU CI, developer laptops, App Service profiles, and non-GPU deployments must remain supported.

Follow the RAPIDS install selector for the target CUDA/Python combination. The repository includes ready-to-use NVIDIA package profiles:

```bash
# CUDA 12 profile
python -m pip install -r deploy/nvidia/requirements-cu12.txt

# CUDA 13 profile
python -m pip install -r deploy/nvidia/requirements-cu13.txt
```

Those requirement files use NVIDIA's Python package index and install the corresponding `nx-cugraph` backend. Verify the current RAPIDS compatibility matrix for the target Python, CUDA, Linux, driver, and GPU combination before building a production image.

The current `nx-cugraph` project supports NetworkX backend dispatch. CEPIO uses that contract rather than importing cuGraph-specific graph types into the CEPIO kernel.

## HTTP API

```text
GET /graph/backend
GET /graph/centrality?algorithm=pagerank
GET /graph/centrality?algorithm=betweenness&sample_size=1000
GET /graph/blast-radius/K-201?max_hops=3&direction=out
GET /graph/communities
```

Graph queries can be narrowed by repeating `relationship_type` and `object_type` query parameters.

Example:

```text
GET /graph/blast-radius/K-201
    ?max_hops=4
    &relationship_type=dependsOn
    &relationship_type=feeds
```

## Python SDK

```python
from cepio.sdk import CEPIOClient

client = CEPIOClient("http://localhost:8000")

critical = client.graph_centrality("pagerank", limit=20)
blast = client.graph_blast_radius(
    "K-201",
    max_hops=3,
    relationship_types=["dependsOn", "feeds"],
)
communities = client.graph_communities()
```

Every result records which backend actually executed the algorithm. In `auto` mode, if cuGraph dispatch fails, CEPIO falls back to NetworkX and reports that fallback in the result metadata.

## Architectural boundary

```text
CEPIO canonical objects + relationships
              |
              v
     GraphAnalyticsEngine
              |
       NetworkX contract
          /       \
         v         v
   NetworkX CPU   nx-cugraph GPU
```

NVIDIA acceleration does not define CEPIO semantics. It accelerates analysis over the canonical CEPIO graph.

## Security note

The first release exposes graph intelligence through the HTTP/SDK surface. It is intentionally **not** added to the MCP facade yet. Policy-scoped graph projection must land first so an agent cannot infer unauthorized topology through centrality scores, communities, or blast-radius results.
