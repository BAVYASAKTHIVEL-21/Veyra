import ThreeGraph from "./ThreeGraph";
import "./Landing.css";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Network,
  Search,
  Globe2,
  Link2,
  ShieldCheck,
} from "lucide-react";
import "./Landing.css";


export default function Landing({
  onGetStarted,
}: {
  onGetStarted: () => void;
}) {

  return (
    <main className="veyra-landing">
      <header className="vl-header">
        <a className="vl-logo" href="#home" aria-label="Veyra home">
          VEYRA<span>.</span>
        </a>

        <div className="vl-powered">
          <Network size={15} />
          <span>Powered by <strong>FalkorDB</strong></span>
        </div>

        <nav className="vl-nav">
          <a href="#about">About</a>
          <button className="vl-nav-cta" onClick={onGetStarted}>
            Start investigation <ArrowUpRight size={16} />
          </button>
        </nav>
      </header>

      <section className="vl-hero" id="home">
        <div className="vl-hero-copy">
          <div className="vl-eyebrow">
            <span className="vl-live-dot" />
            DIGITAL INVESTIGATION PLATFORM
          </div>

          <h1>
            See what
            <br />
            <em>connects.</em>
          </h1>

          <p className="vl-intro">
            Suspicious activity rarely exists in isolation.
            <br className="vl-desktop-break" />
            Follow the evidence. Discover the relationships.
          </p>

          <div className="vl-actions">
            <button className="vl-primary" onClick={onGetStarted}>
              Start investigation <ArrowRight size={17} />
            </button>
            <a className="vl-secondary" href="#about">
              <span className="vl-down-icon"><ArrowDown size={15} /></span>
              Discover Veyra
            </a>
          </div>

          <div className="vl-footnote">
            <span />
            CONNECTED DATA. CLEARER CONTEXT.
          </div>
        </div>

        <div className="vl-scene vl-live-scene">
         <ThreeGraph />
        </div>

        <a href="#about" className="vl-scroll">
          SCROLL TO EXPLORE <ArrowDown size={13} />
        </a>
      </section>

      <section className="vl-about" id="about">
        <div className="vl-about-copy">
          <div className="vl-section-index">01 / ABOUT VEYRA</div>
          <h2>
            Every connection
            <br />
            tells <em>a story.</em>
          </h2>
          <p>
            Veyra helps investigators explore relationships across digital
            identities, websites, and reported activity. Follow connected
            evidence to understand the bigger picture.
          </p>
          <button className="vl-text-link" onClick={onGetStarted}>
            Explore the workspace <ArrowRight size={15} />
          </button>
        </div>

        <div className="vl-about-visual" aria-hidden="true">
          <div className="vl-about-ring ring-one" />
          <div className="vl-about-ring ring-two" />
          <div className="vl-about-ring ring-three" />
          <div className="vl-about-core"><Network size={26} /></div>
          <span className="vl-about-point point-one"><Search size={17} /></span>
          <span className="vl-about-point point-two"><Globe2 size={17} /></span>
          <span className="vl-about-point point-three"><Link2 size={17} /></span>
          <span className="vl-about-point point-four"><ShieldCheck size={17} /></span>
        </div>

        <div className="vl-falkor">
          <div className="vl-section-index">02 / CONNECTED INTELLIGENCE</div>
          <h2>
            Powered by
            <br />
            <em>relationships.</em>
          </h2>
          <p>
            FalkorDB provides the graph layer for exploring how entities
            connect. Veyra uses those relationships to help investigate
            evidence with context.
          </p>
          <a
            className="vl-text-link"
            href="https://www.falkordb.com/"
            target="_blank"
            rel="noreferrer"
          >
            Discover FalkorDB <ArrowUpRight size={15} />
          </a>
        </div>
      </section>

      <section className="vl-closing">
        <div className="vl-section-index">THE NEXT STEP</div>
        <h2>
          Ready to follow
          <br />
          <em>the evidence?</em>
        </h2>
        <p>Start with a signal. Discover the connections around it.</p>
        <button className="vl-primary" onClick={onGetStarted}>
          Enter Veyra <ArrowRight size={17} />
        </button>
      </section>

      <footer className="vl-footer">
        <a className="vl-logo" href="#home">VEYRA<span>.</span></a>
        <span>CONNECTED DATA. EVIDENCE-LED INVESTIGATION.</span>
        <span>GRAPH LAYER · FALKORDB</span>
      </footer>
    </main>
  );
}
