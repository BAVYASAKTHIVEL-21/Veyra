
import { useEffect, useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./GraphExplorer.css";

type RawNode = {
  labels?: string[];
  properties?: Record<string, unknown>;
  id?: string;
  [key: string]: unknown;
};

type RawEdge = {
  from?: Record<string, unknown>;
  to?: Record<string, unknown>;
  relationship?: string;
  source?: string;
  target?: string;
  [key: string]: unknown;
};

type GraphNode = {
  id: string;
  name: string;
  kind: string;
  color: string;
  properties: Record<string, unknown>;
  labels: string[];
  x?: number;
  y?: number;
};

type GraphLink = {
  source: string;
  target: string;
  label: string;
};

type GraphData = {
  nodes: RawNode[];
  edges?: RawEdge[];
  links?: RawEdge[];
  start_id?: string;
  max_hops?: number;
  node_count?: number;
  edge_count?: number;
  path_count?: number;
  truncated?: boolean;
  paths?: Array<{
    start_id: string;
    end_id: string;
    hops: number;
    node_ids: string[];
    relationships: Array<{
      type: string;
      properties?: Record<string, unknown>;
    }>;
  }>;
};

function propertiesOf(node: RawNode) {
  return node.properties ?? node;
}

function idOf(value: unknown): string | undefined {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }

  if (value && typeof value === "object" && "id" in value) {
    const id = (value as { id?: unknown }).id;
    if (typeof id === "string" || typeof id === "number") {
      return String(id);
    }
  }

  return undefined;
}

function nodeKind(labels: string[]) {
  return labels.find((label) => label !== "Entity") ?? "Node";
}

function colorFor(kind: string) {
  switch (kind.toLowerCase()) {
    case "account":
      return "#65d6bd";
    case "domain":
    case "observeddomain":
      return "#a78bfa";
    case "message":
    case "incomingmessage":
      return "#60a5fa";
    case "report":
      return "#fbbf24";
    case "evidence":
      return "#fb7185";
    case "investigation":
    case "case":
      return "#f472b6";
    default:
      return "#8192a8";
  }
}

export default function GraphExplorer() {
  const [raw, setRaw] = useState<GraphData | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [fullRaw, setFullRaw] = useState<GraphData | null>(null);
  const [maxHops, setMaxHops] = useState(3);
  const [investigating, setInvestigating] = useState(false);
  const [graphScope, setGraphScope] = useState<"all" | "entity">("all");
  const [showAllInvestigationConnections, setShowAllInvestigationConnections] = useState(false);
  const [investigationMeta, setInvestigationMeta] =
    useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadGraph() {
    const cacheKey = "veyra:graph:v1";
    let hasCachedGraph = false;

    // Show saved graph data immediately on repeat visits.
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const data = JSON.parse(cached) as GraphData;
        if (Array.isArray(data.nodes) && Array.isArray(data.edges)) {
          setRaw(data);
          setFullRaw(data);
          setGraphScope("all");
          setInvestigationMeta(null);
          setSelected(null);
          hasCachedGraph = true;
        }
      }
    } catch {
      // Ignore malformed or unavailable browser cache.
    }

    setLoading(!hasCachedGraph);
    setError("");

    try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 20000);

      let response: Response;
      try {
        response = await fetch("/api/graph", {
          signal: controller.signal,
          cache: "no-store",
        });
      } finally {
        window.clearTimeout(timeout);
      }

      if (!response.ok) {
        throw new Error(`Graph API returned ${response.status}`);
      }

      const data = (await response.json()) as GraphData;

      if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
        throw new Error("Graph response does not contain nodes and edges arrays.");
      }

      setRaw(data);
      setFullRaw(data);
      setGraphScope("all");
      setInvestigationMeta(null);
      setSelected(null);

      try {
        localStorage.setItem(
          cacheKey,
          JSON.stringify({ ...data, cachedAt: Date.now() }),
        );
      } catch {
        // Cache is optional; keep using live data if storage is unavailable.
      }
    } catch (err) {
      if (!hasCachedGraph) {
        setError(err instanceof Error ? err.message : "Could not load graph.");
      }
    } finally {
      setLoading(false);
    }
  }


  async function investigateSelected() {
    if (!selected) return;

    setInvestigating(true);
    setError("");

    try {
      const params = new URLSearchParams({
        max_hops: String(maxHops),
        limit: "100",
      });

      const response = await fetch(
        `/api/entities/${encodeURIComponent(selected.id)}/graph?${params}`,
        { cache: "no-store" },
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          body.detail || `Investigation failed: ${response.status}`,
        );
      }

      const data = (await response.json()) as GraphData;

      if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
        throw new Error("Investigation returned an invalid graph response.");
      }

      setRaw(data);
      setInvestigationMeta(data);
      setShowAllInvestigationConnections(false);
      setGraphScope("entity");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not investigate this entity.",
      );
    } finally {
      setInvestigating(false);
    }
  }

  useEffect(() => {
    void loadGraph();
  }, []);

  const graph = useMemo(() => {
    if (!raw) return { nodes: [] as GraphNode[], links: [] as GraphLink[] };

    const nodes: GraphNode[] = raw.nodes.map((rawNode, index) => {
      const properties = propertiesOf(rawNode);
      const labels = rawNode.labels ?? [];
      const kind = nodeKind(labels);
      const id = idOf(properties.id ?? rawNode.id) ?? `node-${index}`;

      return {
        id,
        name: String(
          properties.display_name ??
          properties.name ??
          properties.domain ??
          properties.username ??
          properties.id ??
          kind,
        ),
        kind,
        color: colorFor(kind),
        properties,
        labels,
      };
    });

    const ids = new Set(nodes.map((node) => node.id));
    const databaseIdToNodeId = new Map<string, string>();

    raw.nodes.forEach((rawNode, index) => {
      if (rawNode.node_id !== undefined && rawNode.node_id !== null) {
        databaseIdToNodeId.set(
          String(rawNode.node_id),
          nodes[index].id,
        );
      }
    });

    const rawEdges = raw.edges ?? raw.links ?? [];

    const links: GraphLink[] = rawEdges.flatMap((edge) => {
      const source = edge.from_id !== undefined && edge.from_id !== null
        ? databaseIdToNodeId.get(String(edge.from_id)) ?? idOf(edge.from ?? edge.source)
        : idOf(edge.from ?? edge.source);

      const target = edge.to_id !== undefined && edge.to_id !== null
        ? databaseIdToNodeId.get(String(edge.to_id)) ?? idOf(edge.to ?? edge.target)
        : idOf(edge.to ?? edge.target);

      if (!source || !target || !ids.has(source) || !ids.has(target)) {
        return [];
      }

      return [{
        source,
        target,
        label: String(edge.relationship ?? edge.type ?? "CONNECTED"),
      }];
    });

    // In focused investigation mode, show only the selected account
    // and its direct neighbours by default. Keep the full traversal in raw.
    if (graphScope === "entity" && !showAllInvestigationConnections) {
      const rootId = String(investigationMeta?.start_id ?? selected?.id ?? "");
      const directLinks = links.filter(
        (link) => String(link.source) === rootId || String(link.target) === rootId,
      );

      const visibleIds = new Set<string>([rootId]);
      directLinks.forEach((link) => {
        visibleIds.add(String(link.source));
        visibleIds.add(String(link.target));
      });

      return {
        nodes: nodes.filter((node) => visibleIds.has(node.id)),
        links: directLinks,
      };
    }

    return { nodes, links };
  }, [raw, graphScope, showAllInvestigationConnections, investigationMeta, selected]);

  if (loading) {
    return <div className="graph-message">Loading real FalkorDB graph…</div>;
  }

  if (error) {
    return (
      <div className="graph-message graph-error">
        <p>Could not load graph: {error}</p>
        <button onClick={() => void loadGraph()}>Try again</button>
      </div>
    );
  }

  if (!graph.nodes.length) {
    return (
      <div className="graph-message">
        No nodes were returned by FalkorDB.
      </div>
    );
  }

  return (
    <section className="live-graph-layout">
      <div className="live-graph-main">
        <div className="live-graph-toolbar">
          <div>
            <span className="eyebrow">FALKORDB · LIVE DATA</span>
            <h2>Connected evidence</h2>
            <p>
              {graph.nodes.length} returned nodes · {graph.links.length} matched edges
            </p>
          </div>
          <button onClick={() => void loadGraph()}>Refresh graph</button>
        </div>

        {graphScope === "entity" && (
          <div className="graph-investigation-status">
            <p>
              Investigating: <strong>{investigationMeta?.start_id}</strong>
              {" · "}
              {investigationMeta?.node_count ?? 0} nodes
              {" · "}
              {investigationMeta?.edge_count ?? 0} relationships
              {" · "}
              {investigationMeta?.path_count ?? 0} paths
            </p>

            {investigationMeta?.truncated && (
              <p role="status">
                Result limit reached. Additional connected paths may exist.
              </p>
            )}

            <button
              onClick={() => setShowAllInvestigationConnections((value) => !value)}
            >
              {showAllInvestigationConnections
                ? "Show direct connections only"
                : "Show all traversal links"}
            </button>

            <button
              onClick={() => {
                if (fullRaw) setRaw(fullRaw);
                setGraphScope("all");
                setShowAllInvestigationConnections(false);
                setInvestigationMeta(null);
                setSelected(null);
              }}
            >
              Return to full graph
            </button>
          </div>
        )}

        <div className="force-graph-canvas">
          <ForceGraph2D
            graphData={graph}
            backgroundColor="#0a0e14"
            nodeId="id"
            nodeLabel={(node) => {
              const n = node as GraphNode;
              return `${n.name} · ${n.kind}`;
            }}
            nodeColor={(node) => (node as GraphNode).color}
            nodeRelSize={5}
            linkColor={() => "rgba(120, 153, 170, 0.35)"}
            linkWidth={1.2}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={1.5}
            linkDirectionalParticleSpeed={0.003}
            onNodeClick={(node) => setSelected(node as GraphNode)}
            nodeCanvasObject={(node, ctx, globalScale) => {
              const n = node as GraphNode;
              const x = n.x ?? 0;
              const y = n.y ?? 0;

              ctx.beginPath();
              ctx.arc(x, y, 5, 0, 2 * Math.PI);
              ctx.fillStyle = n.color;
              ctx.shadowColor = n.color;
              ctx.shadowBlur = 12;
              ctx.fill();
              ctx.shadowBlur = 0;

              if (globalScale > 1.15) {
                ctx.font = `${Math.max(3, 10 / globalScale)}px sans-serif`;
                ctx.fillStyle = "#dbe7f1";
                ctx.fillText(n.name.slice(0, 32), x + 8, y + 3);
              }
            }}
          />
        </div>

        <div className="graph-legend">
          <span><i style={{ background: "#65d6bd" }} /> Accounts</span>
          <span><i style={{ background: "#a78bfa" }} /> Domains</span>
          <span><i style={{ background: "#60a5fa" }} /> Messages</span>
          <span><i style={{ background: "#fbbf24" }} /> Reports</span>
          <span className="legend-note">Drag nodes · Scroll to zoom · Click to inspect</span>
        </div>
      </div>

      <aside className="graph-inspector">
        <span className="eyebrow">EVIDENCE INSPECTOR</span>
        <h3>{selected ? selected.name : "Select a node"}</h3>

        {selected ? (
          <>
            <span className="graph-kind">{selected.kind}</span>
            <p className="inspector-description">
              These are properties returned by the graph API.
            </p>
            <pre>{JSON.stringify(selected.properties, null, 2)}</pre>

            <div className="entity-investigation-controls">
              <label htmlFor="graph-hop-limit">Maximum hops</label>
              <select
                id="graph-hop-limit"
                value={maxHops}
                onChange={(event) => setMaxHops(Number(event.target.value))}
              >
                <option value={1}>1 hop — direct connections</option>
                <option value={2}>2 hops</option>
                <option value={3}>3 hops</option>
                <option value={4}>4 hops</option>
                <option value={5}>5 hops</option>
              </select>

              <button
                onClick={() => void investigateSelected()}
                disabled={investigating}
              >
                {investigating ? "Querying FalkorDB..." : "Investigate connections"}
              </button>
            </div>
            <button onClick={() => setSelected(null)}>Clear selection</button>
          </>
        ) : (
          <p className="inspector-description">
            Select an account, domain, message, or report in the graph to inspect
            its actual stored properties.
          </p>
        )}
      </aside>
    </section>
  );
}
