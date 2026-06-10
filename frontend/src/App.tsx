import React, { useEffect, useRef, useState } from "react";
import { uploadPdf, chat, chatStream, getMe, resendVerification } from "./lib/api";
import DocLibrary from "./components/DocLibrary";
import Toast from "./components/Toast";
import PdfPanel from "./components/PdfPanel";
import Login from "./components/Login";
import ChatInterface, { Message } from "./components/ChatInterface";
import VerifyEmail from "./components/VerifyEmail";
import ForgotPassword from "./components/ForgotPassword";
import ResetPassword from "./components/ResetPassword";
import ThemeToggle from "./components/ThemeToggle";
import HomePage from "./components/home/HomePage";

/* ───────────── App ───────────── */
export default function App() {
  // Routing state
  const [route, setRoute] = useState<"home" | "login" | "verify-email" | "forgot-password" | "reset-password" | "app">("app");

  // Auth/session
  const [me, setMe] = useState<{ user_id: string; email?: string; email_verified?: boolean } | null>(null);
  const [, setAuthErr] = useState(""); // Used internally but not displayed
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  // current “active” doc id (the one you just uploaded)
  const [docId, setDocId] = useState<string>("");

  // library + scope
  const [docListRefreshKey, setDocListRefreshKey] = useState(0);
  // null = query across all PDFs, string = restrict to that doc
  const [queryScopeDoc, setQueryScopeDoc] = useState<string | null>(null);

  // Chat messages for the chatbot interface
  const [chatMessages, setChatMessages] = useState<Message[]>([]);

  // streaming control
  const [streaming, setStreaming] = useState(false);
  const closeStreamRef = useRef<null | (() => void)>(null);

  // UI state
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  // PDF side panel
  const [showPdf, setShowPdf] = useState<{ docId: string; page: number } | null>(null);

  // Check URL for special routes
  useEffect(() => {
    const path = window.location.pathname;
    const params = new URLSearchParams(window.location.search);
    
    if (path === "/reset-password") {
      setRoute("reset-password");
    } else if (path === "/forgot-password") {
      setRoute("forgot-password");
    } else if (path === "/verify-email" || params.has("token")) {
      setRoute("verify-email");
    } else if (path === "/" && !localStorage.getItem("token")) {
      // Logged-out visitors land on the marketing homepage
      setRoute("home");
    } else {
      setRoute("app");
    }
  }, []);

  // Try to restore session on mount
  useEffect(() => {
    if (route !== "app") return; // Don't check auth for special routes
    
    let cancelled = false;
    (async () => {
      setIsAuthChecking(true);
      try {
        const u = await getMe();
        if (!cancelled) {
          setMe(u);
          setAuthErr("");
          setDocListRefreshKey((k) => k + 1); // load this user's docs
        }
      } catch (e: any) {
        if (!cancelled) {
          setMe(null);
          setAuthErr(e?.message || "Please sign in.");
        }
      } finally {
        if (!cancelled) setIsAuthChecking(false);
      }
    })();
    return () => {
      cancelled = true;
      // safety: close any open SSE on unmount
      closeStreamRef.current?.();
    };
  }, [route]);

  // Handle login success
  function handleLoginSuccess(user: { user_id: string; email?: string; email_verified?: boolean }) {
    setMe(user);
    setAuthErr("");
    setRoute("app");
    window.history.pushState({}, "", "/");
    setDocListRefreshKey((k) => k + 1);
  }

  // Handle resend verification
  async function handleResendVerification() {
    try {
      await resendVerification();
      setNotice("Verification email sent! Check your inbox.");
    } catch (e: any) {
      setError(e.message || "Failed to send verification email");
    }
  }

  // Handle logout
  function handleLogout() {
    localStorage.removeItem("token");
    setMe(null);
    setAuthErr("");
    setDocId("");
    setQueryScopeDoc(null);
    setChatMessages([]);
    setRoute("home");
    window.history.pushState({}, "", "/");
  }

  // Homepage CTAs → auth screen of the app
  function handleEnterApp() {
    setRoute("app");
    window.history.pushState({}, "", "/app");
  }

  async function handleUpload(file: File) {
    if (!me) {
      setError("Please sign in first.");
      return;
    }
    setError(""); setNotice("");
    setStreaming(false);
    setBusy(true);
    try {
      const r = await uploadPdf(file);
      setDocId(r.doc_id);
      setQueryScopeDoc(r.doc_id);            // scope to this doc by default
      setDocListRefreshKey((k) => k + 1);    // refresh library immediately
      setNotice("✅ Uploaded! Indexing in background — wait 10-30 seconds before your first query.");
      
      // Auto-refresh after processing time to update page count
      // Refresh at 3s, 8s, and 15s to catch the updated metadata
      setTimeout(() => setDocListRefreshKey((k) => k + 1), 3000);
      setTimeout(() => setDocListRefreshKey((k) => k + 1), 8000);
      setTimeout(() => setDocListRefreshKey((k) => k + 1), 15000);
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  /**
   * Handle sending a message in the chat interface
   */
  async function handleSendMessage(question: string) {
    setError(""); setNotice("");
    if (!me) { setError("Please sign in first."); return; }
    if (!question.trim()) return;

    const reqId =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : String(Date.now());
    
    const assistantId = reqId + "-assistant";

    // Add user message
    const userMessage: Message = {
      id: reqId,
      type: "user",
      content: question,
      timestamp: Date.now(),
    };

    // Add placeholder for assistant message
    const assistantMessage: Message = {
      id: assistantId,
      type: "assistant",
      content: "",
      citations: [],
      timestamp: Date.now(),
      isStreaming: true,
    };

    setChatMessages((prev) => [...prev, userMessage, assistantMessage]);
    setStreaming(true);

    let finished = false;

    try {
      closeStreamRef.current = chatStream(
        question,
        10, // increased from 5 to 10 for better context
        // onToken: append to assistant message
        (t) => {
          setChatMessages((msgs) =>
            msgs.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + t, isStreaming: true }
                : msg
            )
          );
        },
        // onDone: finalize citations
        (payload) => {
          const c = payload.citations || [];
          setChatMessages((msgs) =>
            msgs.map((msg) =>
              msg.id === assistantId
                ? { ...msg, citations: c, isStreaming: false }
                : msg
            )
          );
          finished = true;
          setStreaming(false);
        },
        // onError: graceful fallback to non-streaming
        async () => {
          closeStreamRef.current?.();
          setStreaming(false);
          if (!finished) {
            try {
              const r = await chat(question, 10, queryScopeDoc || undefined);
              setChatMessages((msgs) =>
                msgs.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: r.answer, citations: r.citations || [], isStreaming: false }
                    : msg
                )
              );
            } catch (e: any) {
              setChatMessages((msgs) =>
                msgs.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: "Sorry, I encountered an error. Please try again.", isStreaming: false }
                    : msg
                )
              );
              setError(e?.message || "Chat failed");
            }
          }
        },
        queryScopeDoc || undefined
      );
    } catch {
      // If EventSource creation fails (rare), non-stream fallback
      setStreaming(false);
      try {
        const r = await chat(question, 10, queryScopeDoc || undefined);
        setChatMessages((msgs) =>
          msgs.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: r.answer, citations: r.citations || [], isStreaming: false }
              : msg
          )
        );
      } catch (e: any) {
        setChatMessages((msgs) =>
          msgs.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: "Sorry, I encountered an error. Please try again.", isStreaming: false }
              : msg
          )
        );
        setError(e?.message || "Chat failed");
      }
    }
  }

  function stopStream() {
    closeStreamRef.current?.();
    setStreaming(false);
    // Update the last assistant message to not be streaming
    setChatMessages((msgs) =>
      msgs.map((msg, idx) =>
        idx === msgs.length - 1 && msg.type === "assistant"
          ? { ...msg, isStreaming: false }
          : msg
      )
    );
  }

  // Handle special routes
  if (route === "home") {
    return <HomePage onSignIn={handleEnterApp} onGetStarted={handleEnterApp} />;
  }

  if (route === "verify-email") {
    return <VerifyEmail onSuccess={() => {
      setRoute("app");
      window.history.pushState({}, "", "/");
      setNotice("Email verified successfully! Welcome!");
      // Refresh user data to get updated verification status
      setDocListRefreshKey((k) => k + 1);
    }} />;
  }

  if (route === "forgot-password") {
    return <ForgotPassword onBack={() => {
      setRoute("app");
      window.history.pushState({}, "", "/");
    }} />;
  }

  if (route === "reset-password") {
    return <ResetPassword onSuccess={() => {
      setRoute("app");
      window.history.pushState({}, "", "/");
      setNotice("Password reset successfully! Please log in.");
    }} />;
  }

  // Show login page if not authenticated
  if (isAuthChecking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-orange-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-2xl mb-4 animate-pulse">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!me) {
    return <Login 
      onLoginSuccess={handleLoginSuccess} 
      onForgotPassword={() => {
        setRoute("forgot-password");
        window.history.pushState({}, "", "/forgot-password");
      }}
    />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 transition-colors">
      {/* Global toasts */}
      {error && <Toast text={error} tone="error" onClose={() => setError("")} />}
      {notice && <Toast text={notice} tone="success" onClose={() => setNotice("")} />}

      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 shadow-sm sticky top-0 z-10 transition-colors">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-white">AI Document Search</h1>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Powered by RAG</p>
                </div>
              </div>
            </div>

            {/* User info & controls */}
            <div className="flex items-center gap-4">
              <ThemeToggle />
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">{me.user_id}</p>
                {me.email && (
                  <div className="flex items-center gap-1">
                    <p className="text-xs text-gray-500 dark:text-gray-400">{me.email}</p>
                    {me.email_verified ? (
                      <span title="Email verified" className="text-green-500">✓</span>
                    ) : (
                      <button
                        onClick={handleResendVerification}
                        title="Click to resend verification email"
                        className="text-xs text-orange-500 hover:underline"
                      >
                        (verify)
                      </button>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Document library + scope */}
        <DocLibrary
          activeDoc={queryScopeDoc}
          refreshKey={docListRefreshKey}
          onSelect={(chosen) => setQueryScopeDoc(chosen)}   // null => all PDFs
          onDeleted={(deletedId) => {
            if (docId === deletedId) setDocId("");
            if (queryScopeDoc === deletedId) setQueryScopeDoc(null);
          }}
        />

        {/* Upload Section */}
        <section className="p-6 bg-white dark:bg-gray-900 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 transition-colors">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Upload Document</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Add PDFs to chat with them</p>
            </div>
            <label className="cursor-pointer group">
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleUpload(f);
                }}
              />
              <span className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-yellow-500 to-orange-600 text-white rounded-lg font-medium hover:from-yellow-600 hover:to-orange-700 transition-all shadow-md group-hover:shadow-lg text-sm">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Upload PDF
              </span>
            </label>
          </div>
            {busy && (
              <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30 px-4 py-2 rounded-lg border border-orange-200 dark:border-orange-800">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-sm font-medium">Processing and indexing...</span>
            </div>
          )}
        </section>

        {/* Chat Interface */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Chat with Your Documents</h2>
            {chatMessages.length > 0 && (
              <button
                onClick={() => {
                  if (window.confirm("Clear all conversation history?")) {
                    setChatMessages([]);
                  }
                }}
                className="text-sm px-3 py-1.5 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Clear Chat
              </button>
            )}
          </div>
          <ChatInterface
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isStreaming={streaming}
            onStopStreaming={stopStream}
            onCitationClick={(docId, page) => setShowPdf({ docId, page })}
          />
        </section>
      </main>

      {/* PDF side panel */}
      {showPdf && (
        <PdfPanel
          docId={showPdf.docId}
          page={showPdf.page}
          onClose={() => setShowPdf(null)}
        />
      )}
    </div>
  );
}
