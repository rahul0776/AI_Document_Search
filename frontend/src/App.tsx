// frontend/src/App.tsx
import { useState } from "react";
import { pingBackend } from "./lib/api";

export default function App() {
  const [msg, setMsg] = useState("");

  return (
    <div className="min-h-screen grid place-items-center bg-gray-50">
      <div className="p-8 rounded-2xl shadow bg-white space-y-4">
        <h1 className="text-3xl font-bold">AI Document Search</h1>

        <button
          className="px-4 py-2 rounded-lg bg-black text-white"
          onClick={async () => {
            try {
              const r = await pingBackend();
              setMsg(r.message);
            } catch (e) {
              setMsg("Could not reach backend");
            }
          }}
        >
          Ping backend
        </button>

        {msg && <p className="text-green-600">{msg}</p>}
      </div>
    </div>
  );
}
