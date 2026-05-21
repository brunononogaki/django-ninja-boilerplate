import { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Head from "next/head";
import { loginUser, loginWithGoogle } from "utils/auth";
import { requestPasswordReset } from "utils/users";

const darkStyles = `
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-16px); }
  }
  .orb { animation: float 8s ease-in-out infinite; }
  .orb-2 { animation: float 10s ease-in-out 2s infinite; }
  .dark-input {
    width: 100%;
    padding: 10px 16px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
  }
  .dark-input::placeholder { color: rgba(255,255,255,0.25); }
  .dark-input:focus { border-color: rgba(99,102,241,0.6); }
  .dark-label {
    display: block;
    font-size: 13px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 6px;
    font-weight: 500;
  }
`;

function ForgotPasswordModal({ isOpen, onClose }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setIsLoading(true);
    try {
      const response = await requestPasswordReset(email);
      setMessage(response.message || "Verifique seu email para resetar a senha");
      setEmail("");
      setTimeout(() => { onClose(); setMessage(""); }, 3000);
    } catch (err) {
      setMessage("Erro ao solicitar reset de senha. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => { setMessage(""); setEmail(""); onClose(); };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center p-4 z-50" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}>
      <div className="rounded-2xl p-8 w-full max-w-md" style={{ background: "#0f0f1a", border: "1px solid rgba(255,255,255,0.1)" }}>
        <h2 className="text-xl font-bold text-white mb-1" style={{ fontFamily: "'Syne', sans-serif" }}>Recuperar Senha</h2>
        <p className="text-sm mb-6" style={{ color: "rgba(255,255,255,0.4)" }}>
          Enviaremos um link de reset para seu email.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {message && (
            <div className="px-4 py-3 rounded-lg text-sm" style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#a5b4fc" }}>
              {message}
            </div>
          )}
          <div>
            <label htmlFor="forgotEmail" className="dark-label">Email</label>
            <input id="forgotEmail" type="email" placeholder="seu@email.com" value={email} onChange={(e) => setEmail(e.target.value)} className="dark-input" required />
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={handleClose} className="flex-1 py-2.5 rounded-xl font-medium text-sm transition-all duration-200" style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.6)", border: "1px solid rgba(255,255,255,0.1)" }}>
              Cancelar
            </button>
            <button type="submit" disabled={isLoading} className="flex-1 py-2.5 rounded-xl font-medium text-sm text-white transition-all duration-200" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              {isLoading ? "Enviando..." : "Enviar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Login() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isForgotPasswordModalOpen, setIsForgotPasswordModalOpen] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      const response = await loginUser(username, password);
      if (response.status_code && response.status_code !== 200) {
        setError(response.message || "Erro ao fazer login");
        setIsLoading(false);
        return;
      }
      router.push("/home");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
        <style>{darkStyles}</style>
      </Head>

      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" style={{ background: "#07070f", fontFamily: "'DM Sans', sans-serif" }}>
        {/* Dot grid */}
        <div className="absolute inset-0" style={{
          backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.18) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%)",
        }} />
        {/* Orbs */}
        <div className="orb absolute rounded-full" style={{ width: 400, height: 400, top: "-100px", left: "-80px", background: "radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)", filter: "blur(40px)" }} />
        <div className="orb-2 absolute rounded-full" style={{ width: 350, height: 350, bottom: "-60px", right: "-60px", background: "radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)", filter: "blur(40px)" }} />

        {/* Card */}
        <div className="relative z-10 w-full max-w-md rounded-2xl p-8" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", backdropFilter: "blur(20px)" }}>
          {/* Back */}
          <Link href="/" className="inline-flex items-center gap-1.5 text-sm mb-7 transition-colors duration-200" style={{ color: "rgba(255,255,255,0.35)" }}
            onMouseEnter={e => e.currentTarget.style.color = "rgba(255,255,255,0.7)"}
            onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.35)"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Voltar
          </Link>

          {/* Header */}
          <h1 className="text-3xl font-bold text-white mb-1 text-center" style={{ fontFamily: "'Syne', sans-serif" }}>Bem-vindo</h1>
          <p className="text-center text-sm mb-8" style={{ color: "rgba(255,255,255,0.35)" }}>Entre na sua conta para continuar</p>

          {/* Error */}
          {error && (
            <div className="mb-5 px-4 py-3 rounded-xl text-sm" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", color: "#fca5a5" }}>
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="username" className="dark-label">Usuário</label>
              <input id="username" type="text" placeholder="Digite seu usuário" value={username} onChange={(e) => setUsername(e.target.value)} className="dark-input" required />
            </div>
            <div>
              <label htmlFor="password" className="dark-label">Senha</label>
              <input id="password" type="password" placeholder="Digite sua senha" value={password} onChange={(e) => setPassword(e.target.value)} className="dark-input" required />
            </div>

            <button type="submit" disabled={isLoading} className="w-full py-3 rounded-xl font-medium text-white text-sm transition-all duration-200 mt-1" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 24px rgba(99,102,241,0.35)" }}>
              {isLoading ? "Entrando..." : "Entrar"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.08)" }} />
            <span className="text-xs" style={{ color: "rgba(255,255,255,0.25)" }}>ou entre com</span>
            <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.08)" }} />
          </div>

          {/* Google */}
          <button type="button" onClick={loginWithGoogle} className="w-full py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-3 transition-all duration-200" style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.75)" }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.09)"}
            onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
          >
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
              <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
              <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"/>
              <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
            </svg>
            Continuar com Google
          </button>

          {/* Footer */}
          <div className="mt-6 space-y-2 text-center">
            <p className="text-sm" style={{ color: "rgba(255,255,255,0.3)" }}>
              Não tem uma conta?{" "}
              <Link href="/registration" className="font-medium transition-colors duration-200" style={{ color: "#818cf8" }}
                onMouseEnter={e => e.currentTarget.style.color = "#a5b4fc"}
                onMouseLeave={e => e.currentTarget.style.color = "#818cf8"}
              >
                Crie sua conta
              </Link>
            </p>
            <button type="button" onClick={() => setIsForgotPasswordModalOpen(true)} className="text-sm transition-colors duration-200" style={{ color: "rgba(255,255,255,0.3)" }}
              onMouseEnter={e => e.currentTarget.style.color = "rgba(255,255,255,0.6)"}
              onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.3)"}
            >
              Esqueci minha senha
            </button>
          </div>
        </div>
      </div>

      <ForgotPasswordModal isOpen={isForgotPasswordModalOpen} onClose={() => setIsForgotPasswordModalOpen(false)} />
    </>
  );
}
