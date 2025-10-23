// frontend/src/components/VerifyEmail.tsx
import React, { useEffect, useState } from "react";
import { verifyEmail } from "../lib/api";

interface VerifyEmailProps {
  onSuccess: () => void;
}

export default function VerifyEmail({ onSuccess }: VerifyEmailProps) {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    // Get token from URL
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (!token) {
      setStatus("error");
      setMessage("No verification token found");
      return;
    }

    // Verify the email
    verifyEmail(token)
      .then((response) => {
        setStatus("success");
        setMessage(response.message || "Email verified successfully!");
        
        // Redirect to main app after 3 seconds
        setTimeout(() => {
          onSuccess();
        }, 3000);
      })
      .catch((error) => {
        setStatus("error");
        setMessage(error.message || "Verification failed. The link may have expired.");
      });
  }, [onSuccess]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-orange-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-2xl p-8">
        {status === "loading" && (
          <div className="text-center">
            <div className="mb-4 animate-spin">
              <svg className="w-16 h-16 mx-auto text-orange-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Verifying Your Email</h2>
            <p className="text-gray-600">Please wait while we verify your email address...</p>
          </div>
        )}

        {status === "success" && (
          <div className="text-center">
            <div className="mb-4">
              <svg className="w-16 h-16 mx-auto text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">✅ Email Verified!</h2>
            <p className="text-gray-600 mb-4">{message}</p>
            <p className="text-sm text-gray-500">Redirecting you to the app...</p>
            <div className="mt-4 flex justify-center">
              <div className="w-48 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-yellow-400 to-orange-500 animate-pulse" style={{ width: "100%" }}></div>
              </div>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="text-center">
            <div className="mb-4">
              <svg className="w-16 h-16 mx-auto text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">❌ Verification Failed</h2>
            <p className="text-gray-600 mb-6">{message}</p>
            <button
              onClick={() => window.location.href = "/"}
              className="w-full bg-gradient-to-r from-yellow-400 to-orange-500 text-white py-2 px-4 rounded-lg font-semibold hover:from-yellow-500 hover:to-orange-600 transition-all"
            >
              Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

