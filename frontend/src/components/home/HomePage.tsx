import { useEffect, useRef } from "react";
import HeroDemo from "./HeroDemo";
import "./homepage.css";

/* Marketing homepage recreated from design_handoff_homepage.
   Working brand name from the design — swap here if renamed. */
const BRAND = "Versed";

type Props = {
  onSignIn: () => void;
  onGetStarted: () => void;
};

function Logo() {
  return (
    <span className="nav-logo">
      <span className="logo-mark"><span></span></span>
      <span className="brand-name">{BRAND}</span>
    </span>
  );
}

export default function HomePage({ onSignIn, onGetStarted }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);

  // Reveal on scroll, with the prototype's fallback: if the observer
  // hasn't fired ~800ms after mount, reveal everything immediately so
  // the page is never left invisible in inert webviews.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const els = Array.from(root.querySelectorAll<HTMLElement>(".reveal"));
    let ioFired = false;
    let io: IntersectionObserver | null = null;
    try {
      io = new IntersectionObserver(
        (entries) => {
          ioFired = true;
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add("in");
              io?.unobserve(e.target);
            }
          });
        },
        { threshold: 0.12 }
      );
      els.forEach((el) => io!.observe(el));
    } catch {
      /* no IntersectionObserver support */
    }
    const fallback = window.setTimeout(() => {
      if (!ioFired) {
        els.forEach((el) => el.classList.add("in", "in-now"));
        io?.disconnect();
      }
    }, 800);
    return () => {
      window.clearTimeout(fallback);
      io?.disconnect();
    };
  }, []);

  return (
    <div className="home" ref={rootRef}>
      <div className="field">
        <span className="orb orb-a"></span>
        <span className="orb orb-b"></span>
        <span className="orb orb-c"></span>
      </div>

      {/* ====== NAV ====== */}
      <nav className="nav">
        <a href="/" onClick={(e) => e.preventDefault()} style={{ textDecoration: "none" }}>
          <Logo />
        </a>
        <ul className="nav-links">
          <li><a href="#how">How it works</a></li>
          <li><a href="#features">Features</a></li>
          <li><a href="#testimonials">Customers</a></li>
          <li><a href="#api">API</a></li>
        </ul>
        <div className="nav-cta">
          <button className="btn btn-ghost" onClick={onSignIn}>Sign in</button>
          <button className="btn btn-primary" onClick={onGetStarted}>Get started</button>
        </div>
      </nav>

      {/* ====== HERO ====== */}
      <header className="hero wrap">
        <div className="hero-badge"><span className="dot"></span>RAG-POWERED · CITATIONS ON EVERY ANSWER</div>
        <h1>Ask your documents <span className="accent-word">anything</span>.</h1>
        <p className="hero-sub">Upload your PDFs and get instant, citation-backed answers — powered by hybrid semantic search.</p>
        <div className="hero-actions">
          <button className="btn btn-primary" onClick={onGetStarted}>Start for free →</button>
          <a className="btn btn-ghost" href="#how">See how it works</a>
        </div>
        <p className="hero-meta">No credit card · Your documents stay private</p>

        <HeroDemo />
      </header>

      {/* ====== TRUST STRIP ====== */}
      <section className="trust wrap reveal">
        <p>Built for the people who live in documents</p>
        <div className="trust-row">
          <span className="trust-chip">Researchers</span>
          <span className="trust-chip">Legal teams</span>
          <span className="trust-chip">Compliance</span>
          <span className="trust-chip">Students</span>
          <span className="trust-chip">Knowledge workers</span>
          <span className="trust-chip">Developers</span>
        </div>
      </section>

      {/* ====== HOW IT WORKS ====== */}
      <section className="section wrap" id="how">
        <div className="section-head reveal">
          <span className="kicker">How it works</span>
          <h2>From PDF to answers in three steps.</h2>
          <p>No setup, no training, no prompt engineering. Drop a document and start asking.</p>
        </div>
        <div className="steps">
          <div className="step-card glass reveal">
            <span className="step-num">01</span>
            <span className="step-icon">↑</span>
            <h3>Upload</h3>
            <p>Drag in any PDF. We extract, chunk, and index it in seconds — encrypted and isolated to your account.</p>
          </div>
          <div className="step-card glass reveal">
            <span className="step-num">02</span>
            <span className="step-icon">?</span>
            <h3>Ask</h3>
            <p>Ask in plain language. Hybrid search blends semantic meaning with exact keywords to find what matters.</p>
          </div>
          <div className="step-card glass reveal">
            <span className="step-num">03</span>
            <span className="step-icon">⌖</span>
            <h3>Verify</h3>
            <p>Every answer streams back with page-level citations. Click one to jump straight to the source passage.</p>
          </div>
        </div>
      </section>

      {/* ====== FEATURES ====== */}
      <section className="section wrap" id="features">
        <div className="section-head reveal">
          <span className="kicker">Features</span>
          <h2>Search that understands, answers you can trust.</h2>
          <p>A production-grade RAG pipeline under the hood — without you ever having to think about it.</p>
        </div>
        <div className="features-grid">
          <div className="feature-card glass reveal">
            <span className="feature-tag">Retrieval</span>
            <h3>Hybrid search</h3>
            <p>Semantic embeddings fused with keyword matching — 30–40% more accurate than either alone.</p>
          </div>
          <div className="feature-card glass reveal">
            <span className="feature-tag">Trust</span>
            <h3>Cited answers</h3>
            <p>Every claim links to the exact page it came from. Verify in one click, never take it on faith.</p>
          </div>
          <div className="feature-card glass reveal">
            <span className="feature-tag">Speed</span>
            <h3>Real-time streaming</h3>
            <p>Answers stream token by token with sub-100ms time to first word. No spinners, no waiting.</p>
          </div>
          <div className="feature-card glass reveal">
            <span className="feature-tag">Privacy</span>
            <h3>Private by design</h3>
            <p>Per-user isolated storage and indexes. Your documents are never shared, pooled, or trained on.</p>
          </div>
          <div className="feature-card glass reveal">
            <span className="feature-tag">Scale</span>
            <h3>Multi-document chat</h3>
            <p>Ask across your whole library or scope to a single file. Context is optimized automatically.</p>
          </div>
          <div className="feature-card glass reveal" id="api">
            <span className="feature-tag">Developers</span>
            <h3>API access</h3>
            <p>Build document Q&A into your own product with a clean REST API and streaming endpoints.</p>
          </div>
        </div>
      </section>

      {/* ====== TESTIMONIALS ====== */}
      <section className="section wrap" id="testimonials">
        <div className="section-head reveal">
          <span className="kicker">Customers</span>
          <h2>Hours of reading, answered in seconds.</h2>
        </div>
        <div className="quotes">
          <div className="quote-card glass reveal">
            <blockquote>I used to spend whole afternoons skimming filings for one number. Now I ask, and the citation takes me right to the page.</blockquote>
            <div className="quote-who">
              <span className="avatar-ph"></span>
              <span>
                <span className="who-name">[Customer name]</span><br />
                <span className="who-role">Compliance analyst</span>
              </span>
            </div>
          </div>
          <div className="quote-card glass reveal">
            <blockquote>The cited answers are the difference. My advisor actually trusts what I bring to meetings now.</blockquote>
            <div className="quote-who">
              <span className="avatar-ph"></span>
              <span>
                <span className="who-name">[Customer name]</span><br />
                <span className="who-role">PhD researcher</span>
              </span>
            </div>
          </div>
          <div className="quote-card glass reveal">
            <blockquote>We wired the API into our intranet in a day. Streaming answers over our policy docs, with sources.</blockquote>
            <div className="quote-who">
              <span className="avatar-ph"></span>
              <span>
                <span className="who-name">[Customer name]</span><br />
                <span className="who-role">Engineering lead</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ====== FINAL CTA ====== */}
      <section className="wrap">
        <div className="cta-final glass reveal">
          <h2>Your documents have the answers.<br />Start asking.</h2>
          <p>Free to start. Upload your first PDF and get a cited answer in under a minute.</p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={onGetStarted}>Get started free →</button>
          </div>
        </div>
      </section>

      {/* ====== FOOTER ====== */}
      <footer>
        <div className="wrap">
          <div className="footer-row">
            <Logo />
            <div className="footer-links">
              <a href="#how">How it works</a>
              <a href="#features">Features</a>
              <a href="#api">API</a>
              <a href="#" onClick={(e) => e.preventDefault()}>Privacy</a>
              <a href="#" onClick={(e) => e.preventDefault()}>Terms</a>
            </div>
          </div>
          <p className="footer-note">© 2026 <span className="brand-name">{BRAND}</span> · Answers with receipts.</p>
        </div>
      </footer>
    </div>
  );
}
