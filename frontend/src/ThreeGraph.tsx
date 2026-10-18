
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

type RawNode = {
  node_id?: number | string;
  labels?: string[];
  properties?: Record<string, unknown>;
};

type RawEdge = {
  from_id?: number | string;
  from_labels?: string[];
  from?: Record<string, unknown>;
  relationship?: string;
  to_id?: number | string;
  to_labels?: string[];
  to?: Record<string, unknown>;
};

type GraphResponse = {
  nodes: RawNode[];
  edges: RawEdge[];
};

type GraphNode = {
  id: string;
  name: string;
  kind: string;
  properties: Record<string, unknown>;
  position: THREE.Vector3;
  mesh: THREE.Mesh;
};

const COLORS: Record<string, number> = {
  account: 0x60a5fa,
  domain: 0xc084fc,
  observedDomain: 0xc084fc,
  url: 0xf97316,
  brand: 0xfb923c,
  report: 0xfb7185,
  evidence: 0x34d399,
  message: 0xfacc15,
  incomingMessage: 0xfacc15,
  post: 0x38bdf8,
  scenario: 0xa78bfa,
  paymentIdentifier: 0xf472b6,
  investigation: 0xf472b6,
  entity: 0x94a3b8,
  node: 0x94a3b8,
};

function nodeId(properties?: Record<string, unknown>) {
  const id = properties?.id ?? properties?.account_id ??
    properties?.domain ?? properties?.username;

  return id === undefined ? undefined : String(id);
}

function nodeName(properties: Record<string, unknown>, kind: string) {
  return String(
    properties.display_name ??
    properties.name ??
    properties.domain ??
    properties.username ??
    properties.id ??
    kind,
  );
}

function nodeColor(kind: string) {
  const exact = COLORS[kind.charAt(0).toLowerCase() + kind.slice(1)];
  if (exact !== undefined) return exact;

  const normalized = kind.toLowerCase();
  if (normalized.includes("account")) return COLORS.account;
  if (normalized.includes("domain")) return COLORS.domain;
  if (normalized.includes("message")) return COLORS.message;
  if (normalized.includes("report")) return COLORS.report;
  if (normalized.includes("evidence")) return COLORS.evidence;
  if (normalized.includes("brand")) return COLORS.brand;
  if (normalized.includes("payment")) return COLORS.paymentIdentifier;
  if (normalized.includes("scenario")) return COLORS.scenario;
  if (normalized.includes("post")) return COLORS.post;
  if (normalized.includes("url") || normalized.includes("link")) return COLORS.url;
  return COLORS.entity;
}

function edgeColor(relationship: string) {
  const type = relationship.toUpperCase();
  if (type.includes("REPORT") || type.includes("BLOCK")) return 0xfb7185;
  if (type.includes("MESSAGE") || type.includes("SENT_TO")) return 0xfacc15;
  if (type.includes("DOMAIN") || type.includes("URL")) return 0xc084fc;
  if (type.includes("PAYMENT")) return 0xf97316;
  if (type.includes("EVIDENCE") || type.includes("SUPPORTED")) return 0x34d399;
  if (type.includes("FRIENDS") || type.includes("CONNECTED")) return 0x60a5fa;
  return 0x64748b;
}

export default function ThreeGraph() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Connecting to graph API…");
  const [error, setError] = useState("");
  const [selection, setSelection] = useState("");

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let disposed = false;
    let frame = 0;
    let graphNodes: GraphNode[] = [];
    let raycaster: THREE.Raycaster;
    let pointer: THREE.Vector2;
    let camera: THREE.PerspectiveCamera;
    let renderer: THREE.WebGLRenderer;

    const scene = new THREE.Scene();
    scene.background = null;

    camera = new THREE.PerspectiveCamera(
      45,
      Math.max(host.clientWidth, 1) / Math.max(host.clientHeight, 1),
      0.1,
      100,
    );
    camera.position.set(0, 0, 10);

    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
      });
    } catch {
      setError("WebGL is unavailable in this browser.");
      setStatus("3D rendering unavailable");
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth, host.clientHeight);
    host.appendChild(renderer.domElement);

    const canvas = renderer.domElement;
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.display = "block";
    canvas.style.touchAction = "none";
    canvas.style.cursor = "grab";

    const tooltip = document.createElement("div");
    tooltip.style.cssText =
      "position:absolute;display:none;z-index:30;pointer-events:none;" +
      "max-width:300px;padding:10px 12px;border:1px solid #334155;" +
      "border-radius:10px;background:rgba(5,10,18,.96);color:#e2e8f0;" +
      "font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;" +
      "overflow-wrap:anywhere;box-shadow:0 8px 30px rgba(0,0,0,.4)";
    host.appendChild(tooltip);

    scene.add(new THREE.AmbientLight(0xffffff, 2));

    const light = new THREE.PointLight(0xffcc00, 15);
    light.position.set(4, 5, 8);
    scene.add(light);

    const graphGroup = new THREE.Group();
    scene.add(graphGroup);

    const edgeMaterial = new THREE.LineBasicMaterial({
      color: 0xff2d95,
      transparent: false,
      opacity: 1.0,
      depthTest: false,
    });

    const edgeLines: THREE.Line[] = [];
    const edgePairs: Array<[string, string]> = [];
    const edgeLabels = new Map<THREE.Line, string>();
    const clock = new THREE.Clock();
    raycaster = new THREE.Raycaster();
    raycaster.params.Line = { threshold: 0.12 };
    pointer = new THREE.Vector2();

    let dragging: GraphNode | null = null;
    let rotating = false;
    let previousX = 0;
    let previousY = 0;

    function getPointer(event: PointerEvent | MouseEvent) {
      const rect = canvas.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
    }

    function onPointerDown(event: PointerEvent) {
      getPointer(event);

      const hit = raycaster.intersectObjects(
        graphNodes.map((node) => node.mesh),
      )[0];

      previousX = event.clientX;
      previousY = event.clientY;

      if (hit) {
        dragging = graphNodes.find((node) => node.mesh === hit.object) ?? null;
        rotating = false;
        if (dragging) setSelection(`${dragging.kind}: ${dragging.name}`);
      } else {
        rotating = true;
      }

      canvas.setPointerCapture(event.pointerId);
    }

    function onPointerMove(event: PointerEvent) {
      if (dragging) {
        const deltaX = event.clientX - previousX;
        const deltaY = event.clientY - previousY;

        dragging.position.x += deltaX * 0.012;
        dragging.position.y -= deltaY * 0.012;
        dragging.mesh.position.copy(dragging.position);

        previousX = event.clientX;
        previousY = event.clientY;
        return;
      }

      if (rotating) {
        graphGroup.rotation.y += (event.clientX - previousX) * 0.005;
        graphGroup.rotation.x += (event.clientY - previousY) * 0.005;

        previousX = event.clientX;
        previousY = event.clientY;
        return;
      }

      getPointer(event);
      const nodeHits = raycaster.intersectObjects(
        graphNodes.map((node) => node.mesh),
      );
      const edgeHits = nodeHits.length
        ? []
        : raycaster.intersectObjects(edgeLines);
      const nodeHit = nodeHits[0];
      const edgeHit = edgeHits[0];

      if (nodeHit) {
        const node = graphNodes.find((item) => item.mesh === nodeHit.object);
        if (node) {
          const color = `#${nodeColor(node.kind).toString(16).padStart(6, "0")}`;
          tooltip.style.display = "block";
          tooltip.style.borderColor = color;
          tooltip.style.left = `${Math.min(event.clientX - canvas.getBoundingClientRect().left + 14, Math.max(8, host!.clientWidth - 315))}px`;
          tooltip.style.top = `${Math.max(8, event.clientY - canvas.getBoundingClientRect().top + 14)}px`;
          tooltip.textContent =
            `${node.kind.toUpperCase()}\n${node.name}\nID: ${node.id}\n` +
            Object.entries(node.properties)
              .filter(([key, value]) => value != null && key !== "id")
              .slice(0, 8)
              .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`)
              .join("\n");
          canvas.style.cursor = "pointer";
        }
      } else if (edgeHit) {
        const line = edgeHit.object as THREE.Line;
        tooltip.style.display = "block";
        tooltip.style.borderColor = "#64748b";
        tooltip.style.left = `${Math.min(event.clientX - canvas.getBoundingClientRect().left + 14, Math.max(8, host!.clientWidth - 315))}px`;
        tooltip.style.top = `${Math.max(8, event.clientY - canvas.getBoundingClientRect().top + 14)}px`;
        tooltip.textContent = `FALKORDB RELATIONSHIP\n${edgeLabels.get(line) ?? "CONNECTED"}`;
        canvas.style.cursor = "crosshair";
      } else {
        tooltip.style.display = "none";
        canvas.style.cursor = "grab";
      }
    }

    function onPointerUp(event: PointerEvent) {
      dragging = null;
      rotating = false;

      if (canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }
    }

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);

    let zoom = 10;

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      zoom = THREE.MathUtils.clamp(zoom + event.deltaY * 0.008, 4, 20);
      camera.position.z = zoom;
    }

    canvas.addEventListener("wheel", onWheel, { passive: false });

    async function loadGraph() {
      const cacheKey = "veyra:graph:v1";

      // Clear any existing Three.js graph before drawing another copy.
      function clearRenderedGraph() {
        for (const node of graphNodes) {
          graphGroup.remove(node.mesh);
          node.mesh.geometry.dispose();
          const material = node.mesh.material;
          if (Array.isArray(material)) material.forEach((m) => m.dispose());
          else material.dispose();
        }
        for (const line of edgeLines) {
          graphGroup.remove(line);
          line.geometry.dispose();
          const material = line.material;
          if (Array.isArray(material)) material.forEach((m) => m.dispose());
          else material.dispose();
        }
        graphNodes.length = 0;
        edgeLines.length = 0;
        edgePairs.length = 0;
        edgeLabels.clear();
      }

      function renderGraph(data: GraphResponse) {
        if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
          throw new Error("The graph API returned an unexpected format.");
        }

        clearRenderedGraph();
        const seen = new Map<string, GraphNode>();
        const databaseIdToNodeId = new Map<string, string>();

        data.nodes.forEach((raw, index) => {
          const properties = raw.properties ?? {};
          const kind = raw.labels?.find((label) => label !== "Entity") ?? "Node";
          const id =
            raw.node_id !== undefined && raw.node_id !== null
              ? String(raw.node_id)
              : nodeId(properties);

          if (!id || seen.has(id)) return;

          const phi = Math.acos(
            -1 + (2 * index) / Math.max(data.nodes.length, 1),
          );
          const theta = Math.sqrt(data.nodes.length * Math.PI) * phi;
          const radius = 7;
          const position = new THREE.Vector3(
            radius * Math.cos(theta) * Math.sin(phi),
            radius * Math.sin(theta) * Math.sin(phi),
            radius * Math.cos(phi),
          );

          const color = nodeColor(kind);
          const mesh = new THREE.Mesh(
            new THREE.SphereGeometry(0.085, 20, 20),
            new THREE.MeshStandardMaterial({
              color,
              emissive: color,
              emissiveIntensity: 0.75,
              roughness: 0.28,
              metalness: 0.18,
            }),
          );
          mesh.userData = { id, kind, name: nodeName(properties, kind) };
          mesh.position.copy(position);
          graphGroup.add(mesh);

          const node: GraphNode = {
            id,
            name: nodeName(properties, kind),
            kind,
            properties,
            position,
            mesh,
          };

          seen.set(id, node);
          if (raw.node_id !== undefined && raw.node_id !== null) {
            databaseIdToNodeId.set(String(raw.node_id), id);
          }
          graphNodes.push(node);
        });

        const validNodes = new Set(seen.keys());

        data.edges.forEach((edge) => {
          const sourceId =
            edge.from_id !== undefined && edge.from_id !== null
              ? databaseIdToNodeId.get(String(edge.from_id)) ??
                nodeId(edge.from)
              : nodeId(edge.from);
          const targetId =
            edge.to_id !== undefined && edge.to_id !== null
              ? databaseIdToNodeId.get(String(edge.to_id)) ??
                nodeId(edge.to)
              : nodeId(edge.to);

          if (
            !sourceId ||
            !targetId ||
            !validNodes.has(sourceId) ||
            !validNodes.has(targetId)
          ) return;

          const source = seen.get(sourceId)!;
          const target = seen.get(targetId)!;
          const geometry = new THREE.BufferGeometry().setFromPoints([
            source.position,
            target.position,
          ]);
          const relationship = edge.relationship || "CONNECTED";
          const material = new THREE.LineBasicMaterial({
            color: edgeColor(relationship),
            transparent: true,
            opacity: 0.72,
            depthTest: true,
          });
          const line = new THREE.Line(geometry, material);
          line.userData = { sourceId, targetId, relationship };
          graphGroup.add(line);
          edgeLines.push(line);
          edgePairs.push([sourceId, targetId]);
          edgeLabels.set(line, relationship);
        });

        if (graphNodes.length === 0) {
          throw new Error("No nodes with usable database IDs were returned.");
        }

        setStatus(
          `Connected · ${graphNodes.length} nodes · ${edgeLines.length} relationships rendered`,
        );
        setError("");
      }

      // First paint: use the shared browser cache without waiting for the API.
      let hasCache = false;
      try {
        const cached = localStorage.getItem(cacheKey);
        if (cached) {
          const parsed = JSON.parse(cached) as GraphResponse;
          if (Array.isArray(parsed.nodes) && Array.isArray(parsed.edges)) {
            renderGraph(parsed);
            hasCache = true;
          }
        }
      } catch {
        // Invalid or old cache: continue with the live API.
      }

      try {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 20000);
        let response: Response;
        try {
          response = await fetch("/api/graph", {
            signal: controller.signal,
            cache: "no-store",
          });
        } finally {
          window.clearTimeout(timeoutId);
        }

        if (!response.ok) {
          throw new Error(`Graph API returned HTTP ${response.status}`);
        }

        const data = (await response.json()) as GraphResponse;
        if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
          throw new Error("The graph API returned an unexpected format.");
        }

        if (disposed) return;

        // Store only a valid response, then render the refreshed graph.
        try {
          localStorage.setItem(
            cacheKey,
            JSON.stringify({ ...data, cachedAt: Date.now() }),
          );
        } catch {
          // Cache storage can be full; rendering can still continue.
        }

        renderGraph(data);
      } catch (err) {
        if (disposed) return;

        if (hasCache) {
          setStatus(
            `Cached graph · ${graphNodes.length} nodes · ${edgeLines.length} relationships`,
          );
          setError("");
        } else {
          setStatus("Graph unavailable");
          setError(
            err instanceof Error ? err.message : "Unable to load graph data.",
          );
        }
      }
    }

    function animate() {
      if (disposed) return;

      frame = requestAnimationFrame(animate);
      const time = clock.getElapsedTime();

      if (!dragging && !rotating) {
        graphGroup.rotation.y += 0.0007;
      }

      graphNodes.forEach((node, index) => {
        const material = node.mesh.material as THREE.MeshStandardMaterial;
        material.emissiveIntensity =
          0.3 + 0.15 * Math.sin(time * 2 + index * 0.7);
      });

      edgeLines.forEach((line, index) => {
        const [sourceId, targetId] = edgePairs[index];
        const source = graphNodes.find((node) => node.id === sourceId);
        const target = graphNodes.find((node) => node.id === targetId);

        if (source && target) {
          line.geometry.setFromPoints([source.position, target.position]);
        }
      });

      renderer.render(scene, camera);
    }

    function resize() {
    if (disposed || !host) return;

    const width = Math.max(host.clientWidth, 1);
    const height = Math.max(host.clientHeight, 1);

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    }

    window.addEventListener("resize", resize);
    void loadGraph();
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);

      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
      canvas.removeEventListener("wheel", onWheel);

      graphGroup.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
          object.geometry.dispose();

          const material = object.material;
          if (Array.isArray(material)) {
            material.forEach((item) => item.dispose());
          } else {
            material.dispose();
          }
        }
      });

      if (host.contains(tooltip)) host.removeChild(tooltip);
      edgeMaterial.dispose();
      renderer.dispose();

      if (host.contains(canvas)) {
        host.removeChild(canvas);
      }
    };
  }, []);

  return (
    <section className="relative h-[420px] min-h-[320px] w-full overflow-hidden rounded-2xl border border-white/5 bg-transparent sm:h-[520px] lg:h-[600px]">
      <div className="pointer-events-none absolute left-3 top-3 z-10 rounded border border-yellow-400/30 bg-black/70 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-yellow-300">
        FalkorDB · 3D evidence graph
      </div>

      <div ref={hostRef} className="absolute inset-0" />

      <div className="pointer-events-none absolute bottom-3 left-3 right-3 z-10 space-y-1">
        <p className="text-xs text-slate-300">{status}</p>
        {selection && (
          <p className="text-xs text-yellow-300">{selection}</p>
        )}
        {error && (
          <p role="alert" className="text-xs text-red-300">
            {error}
          </p>
        )}
      </div>
    </section>
  );
}
