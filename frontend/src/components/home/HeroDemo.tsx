import { useEffect, useState } from "react";

/* Looping "chat with your PDF" hero demo, recreated from
   design_handoff_homepage/hero-demo.js as a state-driven component. */

type Turn = {
  q: string;
  a: string;
  cite: string;
  passage: number;
  page: string;
};

const SCRIPT: Turn[] = [
  {
    q: "What drove revenue growth in Q3?",
    a: "Q3 revenue grew 28% year-over-year, driven primarily by enterprise expansion and the launch of the API tier.",
    cite: "report.pdf · p. 12",
    passage: 0,
    page: "Page 12 of 48",
  },
  {
    q: "Summarize the key risks mentioned.",
    a: "The filing highlights three risks: customer concentration, infrastructure costs, and pending data-residency regulation in the EU.",
    cite: "report.pdf · p. 27",
    passage: 1,
    page: "Page 27 of 48",
  },
];

type Msg = {
  id: number;
  who: "user" | "ai";
  text: string;
  cite?: string;
  thinking?: boolean;
};

const PASSAGE_LINES = [
  ["w90", "w95", "w60"],
  ["w95", "w80"],
];

export default function HeroDemo() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [typed, setTyped] = useState("");
  const [caretVisible, setCaretVisible] = useState(true);
  const [litPassage, setLitPassage] = useState(-1);
  const [pageLabel, setPageLabel] = useState("Page 12 of 48");

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      // Static final state of turn 1, no loop.
      const t = SCRIPT[0];
      setMessages([
        { id: 1, who: "user", text: t.q },
        { id: 2, who: "ai", text: t.a, cite: t.cite },
      ]);
      setLitPassage(t.passage);
      setPageLabel(t.page);
      setCaretVisible(false);
      return;
    }

    let cancelled = false;
    let nextId = 1;
    const wait = (ms: number) =>
      new Promise<void>((resolve) => setTimeout(resolve, ms));

    const addMsg = (msg: Omit<Msg, "id">): number => {
      const id = nextId++;
      // keep only last 4 messages visible
      setMessages((prev) => [...prev, { ...msg, id }].slice(-4));
      return id;
    };

    const updateMsg = (id: number, patch: Partial<Msg>) => {
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
    };

    const typeQuestion = async (text: string) => {
      setTyped("");
      setCaretVisible(true);
      for (let i = 0; i < text.length; i++) {
        if (cancelled) return;
        setTyped(text.slice(0, i + 1));
        await wait(34 + Math.random() * 40);
      }
      await wait(420);
      setTyped("");
      setCaretVisible(false);
    };

    const streamAnswer = async (id: number, text: string, cite: string) => {
      const words = text.split(" ");
      let streamed = "";
      for (let i = 0; i < words.length; i++) {
        if (cancelled) return;
        streamed += (i ? " " : "") + words[i];
        updateMsg(id, { text: streamed });
        await wait(45 + Math.random() * 55);
      }
      updateMsg(id, { cite });
    };

    const playTurn = async (turn: Turn) => {
      setLitPassage(-1);
      await typeQuestion(turn.q);
      if (cancelled) return;
      addMsg({ who: "user", text: turn.q });
      await wait(500);

      const aiId = addMsg({ who: "ai", text: "", thinking: true });
      await wait(1100);
      if (cancelled) return;
      updateMsg(aiId, { thinking: false });

      setPageLabel(turn.page);
      setLitPassage(turn.passage);
      await streamAnswer(aiId, turn.a, turn.cite);
      await wait(3200);
    };

    (async () => {
      await wait(900);
      let i = 0;
      // keep first Q&A visible while second plays; reset after full cycle
      while (!cancelled) {
        if (i % SCRIPT.length === 0 && i > 0) {
          setMessages([]);
          await wait(400);
        }
        await playTurn(SCRIPT[i % SCRIPT.length]);
        i++;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="demo-wrap">
      <div className="demo-glow"></div>
      <div className="demo-window">
        <div className="demo-titlebar">
          <span className="dots"><i></i><i></i><i></i></span>
          <span className="demo-url">app.versed.ai</span>
          <span className="dots" style={{ visibility: "hidden" }}><i></i><i></i><i></i></span>
        </div>
        <div className="demo-body">
          <div className="pdf-pane">
            <span className="pdf-tab"><span className="file-dot"></span>annual-report.pdf</span>
            <div className="pdf-page">
              <div className="pdf-line heading"></div>
              <div className="pdf-line w95"></div>
              <div className="pdf-line w90"></div>
              <div className="pdf-line w70"></div>
              <div className={`pdf-passage${litPassage === 0 ? " lit" : ""}`}>
                {PASSAGE_LINES[0].map((w) => (
                  <div key={w} className={`pdf-line ${w}`}></div>
                ))}
              </div>
              <div className="pdf-line w85"></div>
              <div className="pdf-line w90"></div>
              <div className={`pdf-passage${litPassage === 1 ? " lit" : ""}`}>
                {PASSAGE_LINES[1].map((w) => (
                  <div key={w} className={`pdf-line ${w}`}></div>
                ))}
              </div>
              <div className="pdf-line w70"></div>
            </div>
            <div className="pdf-pageno">{pageLabel}</div>
          </div>
          <div className="chat-pane">
            <div className="chat-scroll">
              {messages.map((m) => (
                <div key={m.id} className={`msg ${m.who}`}>
                  {m.thinking ? (
                    <span className="thinking"><i></i><i></i><i></i></span>
                  ) : m.who === "ai" ? (
                    <>
                      <span className="stream">{m.text}</span>
                      {m.cite && <span className="cite-chip">⌖ {m.cite}</span>}
                    </>
                  ) : (
                    m.text
                  )}
                </div>
              ))}
            </div>
            <div className="chat-input">
              <span className="typed">{typed}</span>
              <span className="caret" style={{ display: caretVisible ? "block" : "none" }}></span>
              <span className="send">↑</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
