// src/components/Toast.tsx
import { useEffect } from "react";

type Props = {
  text: string;
  tone?: "error" | "success";
  timeout?: number;           // ms
  onClose?: () => void;       // called when auto-dismiss or close button
};

export default function Toast({
  text,
  tone = "error",
  timeout = 3500,
  onClose,
}: Props) {
  useEffect(() => {
    const id = setTimeout(() => onClose?.(), timeout);
    return () => clearTimeout(id);
  }, [timeout, onClose]);

  const cls =
    tone === "error"
      ? "bg-red-50 text-red-700 border-red-200"
      : "bg-green-50 text-green-700 border-green-200";

  return (
    <div
      className={`fixed bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded border shadow z-50 ${cls}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span>{text}</span>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-2 text-xs px-2 py-1 rounded border bg-white/70 hover:bg-white"
          >
            Close
          </button>
        )}
      </div>
    </div>
  );
}
