from __future__ import annotations

import importlib.util
import os
from collections.abc import Callable, Iterable
from typing import Any, Literal

import networkx as nx
from pydantic import BaseModel, Field

from .repositories import ObjectRepository

GraphBackend = Literal["auto", "networkx", "cugraph"]
CentralityAlgorithm = Literal["pagerank", "degree", "betweenness", "eigenvector"]
GraphDirection = Literal["out", "in", "both"]


class GraphAnalyticsError(RuntimeError):
    pass


class GraphBackendUnavailable(GraphAnalyticsError):
    pass


class GraphBackendInfo(BaseModel):
    requested: GraphBackend
    selected: Literal["networkx", "cugraph"]
    accelerated: bool
    cugraph_installed: bool
    reason: str | None = None


class GraphNodeScore(BaseModel):
    object_id: str
    object_type: str
    name: str
    score: float


class CentralityResult(BaseModel):
    algorithm: CentralityAlgorithm
    backend: GraphBackendInfo
    node_count: int
    edge_count: int
    relationship_types: list[str] = Field(default_factory=list)
    nodes: list[GraphNodeScore] = Field(default_factory=list)


class BlastRadiusNode(BaseModel):
    object_id: str
    object_type: str
    name: str
    hops: int


class BlastRadiusResult(BaseModel):
    source_id: str
    max_hops: int
    direction: GraphDirection
    backend: GraphBackendInfo
    affected_count: int
    relationship_types: list[str] = Field(default_factory=list)
    nodes: list[BlastRadiusNode] = Field(default_factory=list)


class GraphCommunity(BaseModel):
    community_id: str
    size: int
    members: list[str]


class CommunityResult(BaseModel):
    algorithm: Literal["louvain"] = "louvain"
    backend: GraphBackendInfo
    node_count: int
    edge_count: int
    relationship_types: list[str] = Field(default_factory=list)
    communities: list[GraphCommunity] = Field(default_factory=list)


class GraphAnalyticsEngine:
    """CEPIO graph intelligence with optional RAPIDS nx-cugraph acceleration.

    The CEPIO contract is intentionally NetworkX-compatible. CPU/reference runs use
    NetworkX directly. When ``nx-cugraph`` is installed, ``backend='auto'`` attempts
    supported algorithms on the GPU and fails back to NetworkX without changing the
    CEPIO application contract. ``backend='cugraph'`` is strict and fails closed when
    acceleration is unavailable.
    """

    def __init__(self, repository: ObjectRepository, *, backend: GraphBackend | None = None) -> None:
        requested = backend or os.getenv("CEPIO_GRAPH_BACKEND", "auto").lower()
        if requested not in {"auto", "networkx", "cugraph"}:
            raise ValueError("graph backend must be one of: auto, networkx, cugraph")
        self.repository = repository
        self.backend: GraphBackend = requested  # type: ignore[assignment]

    @staticmethod
    def cugraph_installed() -> bool:
        try:
            return importlib.util.find_spec("nx_cugraph") is not None
        except (ImportError, ValueError):
            return False

    def backend_info(self) -> GraphBackendInfo:
        installed = self.cugraph_installed()
        if self.backend == "networkx":
            return GraphBackendInfo(
                requested=self.backend,
                selected="networkx",
                accelerated=False,
                cugraph_installed=installed,
                reason="CPU/reference backend explicitly selected",
            )
        if installed:
            return GraphBackendInfo(
                requested=self.backend,
                selected="cugraph",
                accelerated=True,
                cugraph_installed=True,
                reason="nx-cugraph is installed; algorithm dispatch will attempt GPU execution",
            )
        if self.backend == "cugraph":
            return GraphBackendInfo(
                requested=self.backend,
                selected="networkx",
                accelerated=False,
                cugraph_installed=False,
                reason="nx-cugraph is not installed; strict cugraph calls will fail",
            )
        return GraphBackendInfo(
            requested=self.backend,
            selected="networkx",
            accelerated=False,
            cugraph_installed=False,
            reason="nx-cugraph is not installed; using NetworkX CPU/reference backend",
        )

    @staticmethod
    def _normalize_filter(values: Iterable[str] | None) -> set[str] | None:
        if values is None:
            return None
        normalized = {value for value in values if value}
        return normalized or None

    def snapshot(
        self,
        *,
        relationship_types: Iterable[str] | None = None,
        object_types: Iterable[str] | None = None,
    ) -> nx.DiGraph:
        relationship_filter = self._normalize_filter(relationship_types)
        object_filter = self._normalize_filter(object_types)
        objects = {
            obj.id: obj
            for obj in self.repository.list_objects()
            if object_filter is None or obj.type in object_filter
        }
        graph = nx.DiGraph()
        for obj in objects.values():
            graph.add_node(obj.id, object_type=obj.type, name=obj.name)

        for obj in objects.values():
            for rel in self.repository.get_relationships(obj.id, direction="out"):
                if rel.target.id not in objects:
                    continue
                if relationship_filter is not None and rel.type not in relationship_filter:
                    continue
                prior = graph.get_edge_data(rel.source.id, rel.target.id, default={})
                rel_types = set(prior.get("relationship_types", ()))
                rel_types.add(rel.type)
                graph.add_edge(
                    rel.source.id,
                    rel.target.id,
                    relationship_types=tuple(sorted(rel_types)),
                    relationship_count=int(prior.get("relationship_count", 0)) + 1,
                )
        return graph

    def _run(
        self,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, GraphBackendInfo]:
        installed = self.cugraph_installed()
        if self.backend == "networkx":
            result = function(*args, **kwargs)
            return result, GraphBackendInfo(
                requested=self.backend,
                selected="networkx",
                accelerated=False,
                cugraph_installed=installed,
                reason="CPU/reference backend explicitly selected",
            )

        if installed:
            try:
                result = function(*args, backend="cugraph", **kwargs)
                return result, GraphBackendInfo(
                    requested=self.backend,
                    selected="cugraph",
                    accelerated=True,
                    cugraph_installed=True,
                    reason="Executed by the RAPIDS nx-cugraph NetworkX backend",
                )
            except Exception as exc:
                if self.backend == "cugraph":
                    raise GraphBackendUnavailable(f"cuGraph execution failed: {exc}") from exc
                result = function(*args, **kwargs)
                return result, GraphBackendInfo(
                    requested=self.backend,
                    selected="networkx",
                    accelerated=False,
                    cugraph_installed=True,
                    reason=f"cuGraph dispatch failed; fell back to NetworkX: {type(exc).__name__}",
                )

        if self.backend == "cugraph":
            raise GraphBackendUnavailable(
                "CEPIO_GRAPH_BACKEND=cugraph requires the RAPIDS nx-cugraph package and a supported NVIDIA GPU runtime"
            )
        result = function(*args, **kwargs)
        return result, GraphBackendInfo(
            requested=self.backend,
            selected="networkx",
            accelerated=False,
            cugraph_installed=False,
            reason="nx-cugraph is not installed; using NetworkX CPU/reference backend",
        )

    @staticmethod
    def _relationship_types(graph: nx.DiGraph) -> list[str]:
        values: set[str] = set()
        for _, _, data in graph.edges(data=True):
            values.update(data.get("relationship_types", ()))
        return sorted(values)

    @staticmethod
    def _node_score(graph: nx.DiGraph, object_id: str, score: float) -> GraphNodeScore:
        data = graph.nodes[object_id]
        return GraphNodeScore(
            object_id=object_id,
            object_type=str(data.get("object_type", "Entity")),
            name=str(data.get("name", object_id)),
            score=float(score),
        )

    def centrality(
        self,
        algorithm: CentralityAlgorithm = "pagerank",
        *,
        relationship_types: Iterable[str] | None = None,
        object_types: Iterable[str] | None = None,
        limit: int = 50,
        sample_size: int | None = None,
    ) -> CentralityResult:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        graph = self.snapshot(relationship_types=relationship_types, object_types=object_types)
        if graph.number_of_nodes() == 0:
            return CentralityResult(
                algorithm=algorithm,
                backend=self.backend_info(),
                node_count=0,
                edge_count=0,
                relationship_types=[],
                nodes=[],
            )

        if algorithm == "pagerank":
            scores, backend = self._run(nx.pagerank, graph)
        elif algorithm == "degree":
            scores, backend = self._run(nx.degree_centrality, graph)
        elif algorithm == "betweenness":
            kwargs: dict[str, Any] = {"normalized": True}
            if sample_size is not None:
                if sample_size < 1:
                    raise ValueError("sample_size must be >= 1")
                kwargs["k"] = min(sample_size, graph.number_of_nodes())
            scores, backend = self._run(nx.betweenness_centrality, graph, **kwargs)
        elif algorithm == "eigenvector":
            scores, backend = self._run(nx.eigenvector_centrality, graph, max_iter=1000)
        else:
            raise ValueError(f"Unsupported centrality algorithm: {algorithm}")

        ranked = sorted(
            (self._node_score(graph, object_id, score) for object_id, score in scores.items()),
            key=lambda item: (-item.score, item.object_id),
        )[:limit]
        return CentralityResult(
            algorithm=algorithm,
            backend=backend,
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            relationship_types=self._relationship_types(graph),
            nodes=ranked,
        )

    def blast_radius(
        self,
        source_id: str,
        *,
        max_hops: int = 3,
        direction: GraphDirection = "out",
        relationship_types: Iterable[str] | None = None,
        object_types: Iterable[str] | None = None,
    ) -> BlastRadiusResult:
        if max_hops < 1:
            raise ValueError("max_hops must be >= 1")
        graph = self.snapshot(relationship_types=relationship_types, object_types=object_types)
        if source_id not in graph:
            raise KeyError(f"Unknown CEPIO graph object: {source_id}")
        traversal: nx.Graph | nx.DiGraph
        if direction == "out":
            traversal = graph
        elif direction == "in":
            traversal = graph.reverse(copy=False)
        elif direction == "both":
            traversal = graph.to_undirected()
        else:
            raise ValueError("direction must be one of: out, in, both")

        distances, backend = self._run(
            nx.single_source_shortest_path_length,
            traversal,
            source_id,
            cutoff=max_hops,
        )
        nodes = []
        for object_id, hops in distances.items():
            if object_id == source_id:
                continue
            data = graph.nodes[object_id]
            nodes.append(
                BlastRadiusNode(
                    object_id=object_id,
                    object_type=str(data.get("object_type", "Entity")),
                    name=str(data.get("name", object_id)),
                    hops=int(hops),
                )
            )
        nodes.sort(key=lambda item: (item.hops, item.object_id))
        return BlastRadiusResult(
            source_id=source_id,
            max_hops=max_hops,
            direction=direction,
            backend=backend,
            affected_count=len(nodes),
            relationship_types=self._relationship_types(graph),
            nodes=nodes,
        )

    def communities(
        self,
        *,
        relationship_types: Iterable[str] | None = None,
        object_types: Iterable[str] | None = None,
    ) -> CommunityResult:
        graph = self.snapshot(relationship_types=relationship_types, object_types=object_types)
        if graph.number_of_nodes() == 0:
            return CommunityResult(
                backend=self.backend_info(),
                node_count=0,
                edge_count=0,
                relationship_types=[],
                communities=[],
            )
        undirected = graph.to_undirected()
        groups, backend = self._run(nx.community.louvain_communities, undirected, seed=42)
        normalized = [sorted(str(member) for member in group) for group in groups]
        normalized.sort(key=lambda members: (-len(members), members))
        communities = [
            GraphCommunity(community_id=f"community-{index}", size=len(members), members=members)
            for index, members in enumerate(normalized, start=1)
        ]
        return CommunityResult(
            backend=backend,
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
            relationship_types=self._relationship_types(graph),
            communities=communities,
        )
