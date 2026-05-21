import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { getSocialToken } from "utils/auth";

export default function GoogleCallback() {
  const router = useRouter();
  const [error, setError] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      try {
        await getSocialToken();
        router.push("/home");
      } catch (err) {
        console.error("Erro ao gerar JWT:", err);
        setError(err.message || "Erro ao processar autenticação. Tente novamente.");
      }
    };

    handleCallback();
  }, [router]);

  return (
    <>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
      </Head>

      <div className="min-h-screen flex items-center justify-center" style={{ background: "#07070f", fontFamily: "'DM Sans', sans-serif" }}>
        {/* Dot grid */}
        <div className="absolute inset-0" style={{
          backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(ellipse 60% 60% at 50% 50%, black 30%, transparent 100%)",
        }} />

        <div className="relative z-10 text-center px-6">
          {!error ? (
            <>
              {/* Spinner */}
              <div className="flex justify-center mb-8">
                <div className="relative w-14 h-14">
                  <div className="absolute inset-0 rounded-full" style={{ border: "2px solid rgba(99,102,241,0.15)" }} />
                  <div className="absolute inset-0 rounded-full animate-spin" style={{ border: "2px solid transparent", borderTopColor: "#818cf8" }} />
                </div>
              </div>
              <p className="text-white font-medium mb-1">Autenticando...</p>
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>Aguarde um momento</p>
            </>
          ) : (
            <>
              <div className="flex justify-center mb-6">
                <div className="w-14 h-14 rounded-full flex items-center justify-center" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ color: "#f87171" }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              </div>
              <p className="text-white font-medium mb-2">Erro na autenticação</p>
              <p className="text-sm mb-8 max-w-xs mx-auto" style={{ color: "rgba(255,255,255,0.35)" }}>{error}</p>
              <button onClick={() => router.push("/")} className="px-6 py-2.5 rounded-xl text-sm font-medium text-white transition-all duration-200" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
                Voltar ao início
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
