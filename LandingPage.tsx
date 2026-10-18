
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Fingerprint,
  FileSearch,
  GitBranch,
  Network,
  ScanSearch,
  ShieldCheck,
} from "lucide-react";
import "./LandingPage.css";

type LandingPageProps = {
  onGetStarted: () => void;
};

const investigationSteps = [
  {
    number: "01",
    title: "Analyze",
    description: "Inspect a suspicious message, URL, or account.",
    icon: ScanSearch,
  },
  {
    number: "02",
    title: "Connect",
    description: "Trace related entities through FalkorDB.",
    icon: GitBranch,
  },
  {
    number: "03",
    title: "Investigate",
    description: "Examine connected records and supporting evidence.",
    icon: FileSearch,
  },
  {
    number: "04",
    title: "Understand",
    description: "Review findings with context and uncertainty.",
    icon: ShieldCheck,
  },
];

function EvidenceBoard() {
  return (
    <div className="evidence-board">
      <div className="board-topline">
        <div className="board-brand">
          <Fingerprint size={17} />
          <span>VE YRA / INTELLIGENCE</span>
        </div>
        <span className="board-case">CASE FILE · 001</span>
      </div>

      <div className="board-heading">
        <div>
          <span className="board-kicker">CONNECTED EVIDENCE</span>
          <h2>Look beyond the signal.</h2>
        </div>
        <div className="engine-mark">
          <Network size={18} />
          <span>FalkorDB</span>
        </div>
      </div>

      <div className="evidence-map">
        <svg
          className="evidence-lines"
          viewBox="0 0 520 300"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <g className="map-lines">
            <path d="M100 66 L250 132" />
            <path d="M250 132 L414 60" />
            <path d="M250 132 L114 242" />
            <path d="M250 132 L410 239" />
            <path d="M100 66 L114 242" />
            <path d="M414 60 L410 239" />
            <path d="M114 242 L250 132" />
          </g>
        </svg>

        <div className="evidence-node node-account">
          <div className="evidence-node-icon">
            <Fingerprint size={18} />
          </div>
          <span className="evidence-node-label">ACCOUNT</span>
          <strong>Identity</strong>
        </div>

        <div className="evidence-node node-message">
          <div className="evidence-node-icon">
            <ScanSearch size={18} />
          </div>
          <span className="evidence-node-label">MESSAGE</span>
          <strong>Signal</strong>
        </div>

        <div className="evidence-node node-domain">
          <div className="evidence-node-icon">
            <Network size={18} />
          </div>
          <span className="evidence-node-label">DOMAIN</span>
          <strong>Infrastructure</strong>
        </div>

        <div className="evidence-node node-link">
          <div className="evidence-node-icon">
            <GitBranch size={18} />
          </div>
          <span className="evidence-node-label">RELATIONSHIP</span>
          <strong>Connection</strong>
        </div>

        <div className="evidence-node node-report">
          <div className="evidence-node-icon">
            <FileSearch size={18} />
          </div>
          <span className="evidence-node-label">EVIDENCE</span>
          <strong>Records</strong>
        </div>

        <div className="board-center">
          <span>GRAPH</span>
          <strong>F</strong>
          <small>FALKORDB</small>
        </div>
      </div>

      <div className="board-footer">
        <span>GRAPH-BASED INVESTIGATION</span>
        <span className="board-footer-separator" />
        <span>ILLUSTRATIVE MODEL</span>
      </div>
    </div>
  );
}

export default function LandingPage({
  onGetStarted,
}: LandingPageProps) {
  return (
    <div className="veyra-landing" id="home">
      <header className="landing-nav">
        <a className="landing-brand" href="#home" aria-label="Veyra home">
          <span className="brand-symbol">V</span>
          <span className="brand-name">
            VEYRA<span>.</span>
          </span>
        </a>

        <nav className="landing-links" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#falkordb">FalkorDB</a>
          <a href="#principles">Our approach</a>
        </nav>

        <button
          className="landing-nav-cta"
          onClick={onGetStarted}
          type="button"
        >
          Open workspace <ArrowUpRight size={16} />
        </button>
      </header>

      <main>
        <section className="landing-hero">
          <div className="hero-copy">
            <div className="hero-eyebrow">
              <span className="eyebrow-rule" />
              DIGITAL INVESTIGATION PLATFORM
            </div>

            <h1>
              The truth is rarely in{" "}
              <span>one place.</span>
            </h1>

            <p className="hero-description">
              Veyra investigates suspicious messages, accounts, links, and
              domains by uncovering the relationships between them.
            </p>

            <p className="hero-description secondary-description">
              Powered by graph-based investigation with{" "}
              <strong>FalkorDB.</strong>
            </p>

            <div className="hero-actions">
              <button
                className="primary-cta"
                onClick={onGetStarted}
                type="button"
              >
                Start investigation
                <ArrowRight size={17} />
              </button>

              <a className="secondary-cta" href="#how-it-works">
                See how it works
                <ArrowDownRight size={16} />
              </a>
            </div>

            <div className="hero-meta">
              <span>01 / CONNECTED INTELLIGENCE</span>
              <span>GRAPH-POWERED · FALKORDB</span>
            </div>
          </div>

          <div className="hero-visual">
            <EvidenceBoard />
            <div className="hero-visual-caption">
              <span className="caption-mark" />
              <span>FROM SIGNAL TO CONNECTION</span>
            </div>
          </div>
        </section>

        <section className="platform-strip" id="falkordb">
          <div className="platform-strip-label">
            <span>THE ENGINE</span>
            <strong>FalkorDB</strong>
          </div>
          <p>
            A graph database that lets Veyra explore entities and their
            relationships—not just isolated indicators.
          </p>
          <a
            href="https://www.falkordb.com/"
            target="_blank"
            rel="noreferrer"
            className="platform-link"
          >
            Explore FalkorDB <ArrowUpRight size={15} />
          </a>
        </section>

        <section className="workflow-section" id="how-it-works">
          <div className="section-intro">
            <span className="section-kicker">THE INVESTIGATION PROCESS</span>
            <h2>
              One signal.
              <br />
              <span>A wider picture.</span>
            </h2>
            <p>
              Follow the evidence from the initial message to the
              relationships that provide context.
            </p>
          </div>

          <div className="workflow-list">
            {investigationSteps.map((step) => {
              const Icon = step.icon;

              return (
                <article className="workflow-row" key={step.number}>
                  <span className="workflow-number">{step.number}</span>
                  <div className="workflow-icon">
                    <Icon size={20} strokeWidth={1.6} />
                  </div>
                  <div className="workflow-copy">
                    <h3>{step.title}</h3>
                    <p>{step.description}</p>
                  </div>
                  <ArrowUpRight
                    className="workflow-arrow"
                    size={18}
                    strokeWidth={1.5}
                  />
                </article>
              );
            })}
          </div>
        </section>

        <section className="principles-section" id="principles">
          <div className="principle-heading">
            <span className="section-kicker">BUILT FOR INVESTIGATION</span>
            <h2>Evidence before assumptions.</h2>
          </div>

          <div className="principle-grid">
            <article>
              <span className="principle-index">A / 01</span>
              <h3>Connected context</h3>
              <p>
                Explore links between accounts, domains, messages, and
                available records.
              </p>
            </article>

            <article>
              <span className="principle-index">A / 02</span>
              <h3>Traceable findings</h3>
              <p>
                Review the records and relationships behind an
                investigation result.
              </p>
            </article>

            <article>
              <span className="principle-index">A / 03</span>
              <h3>Responsible assessment</h3>
              <p>
                Treat connected reports as evidence to examine, not
                automatic proof of wrongdoing.
              </p>
            </article>
          </div>
        </section>

        <section className="landing-bottom-cta">
          <div>
            <span className="section-kicker">YOUR INVESTIGATION STARTS HERE</span>
            <h2>Look beyond the message.</h2>
            <p>
              Open the Veyra workspace to analyze a message and explore
              connected evidence.
            </p>
          </div>

          <button
            className="primary-cta"
            onClick={onGetStarted}
            type="button"
          >
            Open workspace <ArrowUpRight size={17} />
          </button>
        </section>
      </main>

      <footer className="landing-footer">
        <a className="landing-brand" href="#home" aria-label="Veyra home">
          <span className="brand-symbol">V</span>
          <span className="brand-name">
            VEYRA<span>.</span>
          </span>
        </a>
        <span className="footer-description">
          Connected intelligence for digital trust.
        </span>
        <span className="footer-engine">GRAPH POWERED / FALKORDB</span>
      </footer>
    </div>
  );
}
