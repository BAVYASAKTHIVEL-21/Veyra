import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import InvestigationWorkspace from "./InvestigationWorkspace";

type VeyraWorkspaceRequest = {
  text: string;
  simulatorMessageId?: string | null;
  conversationId?: string | null;
  senderUsername?: string | null;
  senderAccountId?: string | null;
  senderDisplayName?: string | null;
  senderUiVerified?: boolean;
  scenarioId?: string | null;
};

declare global {
  interface Window {
    openVeyraWorkspace?: (request: string | VeyraWorkspaceRequest) => void;
  }
}

function setVeyraUnderlyingPage(hidden: boolean) {
  const main = document.querySelector<HTMLElement>("main");
  const footer = document.querySelector<HTMLElement>("footer");
  const cases = document.getElementById("view-cases");
  const investigation = document.getElementById("view-new-investigation");

  if (main) main.style.display = hidden ? "none" : "";
  if (footer) footer.style.display = hidden ? "none" : "";

  // Hide legacy page panels without touching the shared navigation header.
  if (cases) cases.classList.toggle("hidden", hidden);
  if (investigation) investigation.classList.toggle("hidden", hidden);
}

function setVeyraBackgroundAnimation(hidden: boolean) {
  document.querySelectorAll<HTMLElement>(
    ".diagonal-sweep-1, .diagonal-sweep-2"
  ).forEach((element) => {
    if (hidden) {
      if (!element.dataset.veyraOriginalVisibility) {
        element.dataset.veyraOriginalVisibility = element.style.visibility || "visible";
        element.dataset.veyraOriginalOpacity = element.style.opacity || "";
        element.dataset.veyraOriginalAnimation = element.style.animation || "";
      }
      element.style.setProperty("visibility", "hidden", "important");
      element.style.setProperty("opacity", "0", "important");
      element.style.setProperty("animation", "none", "important");
    } else {
      element.style.removeProperty("visibility");
      element.style.removeProperty("opacity");
      element.style.removeProperty("animation");
      delete element.dataset.veyraOriginalVisibility;
      delete element.dataset.veyraOriginalOpacity;
      delete element.dataset.veyraOriginalAnimation;
    }
  });
}

function WorkspaceOverlay() {
  const [request, setRequest] = useState<{
    id: number;
    message: string;
    metadata: VeyraWorkspaceRequest | null;
  } | null>(null);

  React.useEffect(() => {
    // Let the existing Veyra navigation control all non-investigation views.
    const handleVeyraNavigation = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;

      const link = target.closest<HTMLAnchorElement>("a[data-veyra-view]");
      if (!link) return;

      const view = link.dataset.veyraView;
      const host = document.getElementById("veyra-react-workspace-host");

      if (view === "investigate") {
        event.preventDefault();
        event.stopPropagation();

        window.location.hash = "#investigate";
        window.openVeyraWorkspace?.({ text: "" });
        return;
      }

      // Close the workspace, but do not override the clicked navigation route.
      if (host) {
        host.style.display = "none";
      }
      document.documentElement.classList.remove("veyra-investigation-open");
      document.body.classList.remove("veyra-investigation-open");
      setVeyraUnderlyingPage(false);
      setVeyraBackgroundAnimation(false);
      setRequest(null);
    };

    const handleWorkspaceCloseRequest = () => closeWorkspace();

    window.addEventListener(
      "veyra:workspace-close-request",
      handleWorkspaceCloseRequest
    );

    document.addEventListener("click", handleVeyraNavigation, true);

    window.openVeyraWorkspace = (input: string | VeyraWorkspaceRequest) => {
      const normalized: VeyraWorkspaceRequest =
        typeof input === "string" ? { text: input } : input;

      setRequest({
        id: Date.now(),
        message: normalized.text,
        metadata: normalized
      });

      const host = document.getElementById("veyra-react-workspace-host");
      if (host) {
        host.classList.remove("hidden");
        host.style.display = "block";
      }

      document.documentElement.classList.add("veyra-investigation-open");
      document.body.classList.add("veyra-investigation-open");
      setVeyraUnderlyingPage(false);
      setVeyraBackgroundAnimation(true);
    };

    return () => {
      document.removeEventListener(
        "click",
        handleVeyraNavigation,
        true
      );
      window.removeEventListener(
        "veyra:workspace-close-request",
        handleWorkspaceCloseRequest
      );
      delete window.openVeyraWorkspace;
    };
  }, []);

  function closeWorkspace() {
    const host = document.getElementById("veyra-react-workspace-host");

    // Hide the React investigation overlay and return to the existing Veyra UI.
    if (host) {
      host.classList.add("hidden");
      host.style.display = "none";
    }

    document.documentElement.classList.remove("veyra-investigation-open");
    document.body.classList.remove("veyra-investigation-open");
    setVeyraUnderlyingPage(false);
    setVeyraBackgroundAnimation(false);
    setRequest(null);

    window.dispatchEvent(new CustomEvent("veyra:workspace-closed"));
  }

  if (!request) return null;

  return (
    <div className="relative min-h-screen w-full overflow-y-auto bg-[#070709] text-white">

      <InvestigationWorkspace
        key={request.id}
        initialMessage={request.message || null}
        initialMetadata={request.metadata}
        onClose={closeWorkspace}
      />
    </div>
  );
}

const host = document.getElementById("veyra-react-workspace-root");
if (host) createRoot(host).render(<WorkspaceOverlay />);
