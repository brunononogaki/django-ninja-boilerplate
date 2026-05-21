import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { isAuthenticated, logoutUser } from "utils/auth";
import { getCurrentUser, updateUser, changeUserPassword } from "utils/users";

const darkStyles = `
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
  .dark-input::placeholder { color: rgba(255,255,255,0.2); }
  .dark-input:focus { border-color: rgba(99,102,241,0.6); }
  .dark-input:disabled { opacity: 0.4; cursor: not-allowed; }
  .dark-label {
    display: block;
    font-size: 12px;
    color: rgba(255,255,255,0.4);
    margin-bottom: 6px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
`;

function ChangePasswordModal({ isOpen, userId, onClose }) {
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const [form, setForm] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const validate = () => {
    if (!form.currentPassword) { setMsg({ type: "error", text: "Informe sua senha atual" }); return false; }
    if (!form.newPassword) { setMsg({ type: "error", text: "Informe a nova senha" }); return false; }
    if (form.newPassword.length < 8) { setMsg({ type: "error", text: "A nova senha deve ter pelo menos 8 caracteres" }); return false; }
    if (form.newPassword !== form.confirmPassword) { setMsg({ type: "error", text: "As senhas não correspondem" }); return false; }
    if (form.currentPassword === form.newPassword) { setMsg({ type: "error", text: "A nova senha deve ser diferente da atual" }); return false; }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMsg({ type: "", text: "" });
    if (!validate()) return;
    setIsChangingPassword(true);
    try {
      await changeUserPassword(userId, form.currentPassword, form.newPassword);
      setMsg({ type: "success", text: "Senha alterada com sucesso!" });
      setForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setTimeout(() => { onClose(); setMsg({ type: "", text: "" }); }, 2000);
    } catch (error) {
      setMsg({ type: "error", text: error.message || "Erro ao alterar senha" });
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleClose = () => {
    setForm({ currentPassword: "", newPassword: "", confirmPassword: "" });
    setMsg({ type: "", text: "" });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center p-4 z-50" style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}>
      <div className="w-full max-w-md rounded-2xl p-8" style={{ background: "#0f0f1a", border: "1px solid rgba(255,255,255,0.1)" }}>
        <h2 className="text-lg font-bold text-white mb-1" style={{ fontFamily: "'Syne', sans-serif" }}>Alterar Senha</h2>
        <p className="text-sm mb-6" style={{ color: "rgba(255,255,255,0.35)" }}>Escolha uma senha segura</p>

        {msg.text && (
          <div className="mb-5 px-4 py-3 rounded-xl text-sm" style={msg.type === "success"
            ? { background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)", color: "#86efac" }
            : { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", color: "#fca5a5" }}>
            {msg.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="dark-label">Senha Atual</label>
            <input type="password" name="currentPassword" value={form.currentPassword} onChange={handleChange} placeholder="••••••••" disabled={isChangingPassword} className="dark-input" />
          </div>
          <div>
            <label className="dark-label">Nova Senha</label>
            <input type="password" name="newPassword" value={form.newPassword} onChange={handleChange} placeholder="Mín. 8 caracteres" disabled={isChangingPassword} className="dark-input" />
          </div>
          <div>
            <label className="dark-label">Confirmar Nova Senha</label>
            <input type="password" name="confirmPassword" value={form.confirmPassword} onChange={handleChange} placeholder="••••••••" disabled={isChangingPassword} className="dark-input" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={isChangingPassword} className="flex-1 py-2.5 rounded-xl font-medium text-sm text-white transition-all duration-200" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
              {isChangingPassword ? "Alterando..." : "Alterar"}
            </button>
            <button type="button" onClick={handleClose} disabled={isChangingPassword} className="flex-1 py-2.5 rounded-xl font-medium text-sm transition-all duration-200" style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.55)", border: "1px solid rgba(255,255,255,0.1)" }}>
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [formData, setFormData] = useState({ username: "", first_name: "", last_name: "", email: "" });
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) { router.push("/"); return; }

    const fetchUser = async () => {
      try {
        const userData = await getCurrentUser();
        if (userData.status_code && userData.status_code !== 200) { logoutUser(); router.push("/"); return; }
        setUser(userData);
        setFormData({ username: userData.username || "", first_name: userData.first_name || "", last_name: userData.last_name || "", email: userData.email || "" });
      } catch (error) {
        console.error("Erro ao buscar dados do usuário:", error);
        logoutUser(); router.push("/");
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  const handleLogout = async () => { await logoutUser(); router.push("/"); };

  const handleEditToggle = () => {
    if (isEditing) setFormData({ username: user?.username || "", first_name: user?.first_name || "", last_name: user?.last_name || "", email: user?.email || "" });
    setIsEditing(!isEditing);
  };

  const handleInputChange = (e) => setFormData((p) => ({ ...p, [e.target.name]: e.target.value }));

  const handleSave = async () => {
    setIsSaving(true);
    setMessage({ type: "", text: "" });
    try {
      const updatedUser = await updateUser(user.id, formData);
      setUser(updatedUser);
      setIsEditing(false);
      setMessage({ type: "success", text: "Dados atualizados com sucesso!" });
      setTimeout(() => setMessage({ type: "", text: "" }), 3000);
    } catch (error) {
      setMessage({ type: "error", text: error.message || "Erro ao conectar com o servidor" });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#07070f" }}>
        <div className="relative w-10 h-10">
          <div className="absolute inset-0 rounded-full" style={{ border: "2px solid rgba(99,102,241,0.15)" }} />
          <div className="absolute inset-0 rounded-full animate-spin" style={{ border: "2px solid transparent", borderTopColor: "#818cf8" }} />
        </div>
      </div>
    );
  }

  const initials = [user?.first_name, user?.last_name].filter(Boolean).map(n => n[0]).join("").toUpperCase() || user?.username?.[0]?.toUpperCase() || "?";
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username;

  return (
    <>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
        <style>{darkStyles}</style>
      </Head>

      <div className="min-h-screen relative overflow-hidden" style={{ background: "#07070f", fontFamily: "'DM Sans', sans-serif" }}>
        {/* Dot grid */}
        <div className="absolute inset-0" style={{
          backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.12) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(ellipse 100% 60% at 50% 0%, black 40%, transparent 100%)",
        }} />

        {/* Top nav */}
        <nav className="relative z-10 flex items-center justify-between px-6 py-4 mx-auto max-w-4xl">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }} />
            <span className="font-semibold text-white text-sm">MyApp</span>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-xl transition-all duration-200" style={{ color: "rgba(255,255,255,0.45)", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
            onMouseEnter={e => e.currentTarget.style.color = "rgba(255,255,255,0.75)"}
            onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.45)"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h6a2 2 0 012 2v1" />
            </svg>
            Sair
          </button>
        </nav>

        {/* Content */}
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-8">

          {/* Profile header */}
          <div className="flex items-center gap-4 mb-8">
            <div className="w-14 h-14 rounded-2xl flex-shrink-0 overflow-hidden" style={!user?.avatar_url ? { background: "linear-gradient(135deg, #6366f1, #8b5cf6)" } : {}}>
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={displayName} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-white font-bold text-lg">{initials}</div>
              )}
            </div>
            <div>
              <h1 className="text-xl font-bold text-white" style={{ fontFamily: "'Syne', sans-serif" }}>{displayName}</h1>
              <p className="text-sm" style={{ color: "rgba(255,255,255,0.35)" }}>{user?.email}</p>
            </div>
          </div>

          {/* Card */}
          <div className="rounded-2xl p-6" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold text-white" style={{ fontFamily: "'Syne', sans-serif", letterSpacing: "0.03em" }}>Informações do Perfil</h2>
              {!isEditing && (
                <button onClick={handleEditToggle} className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-all duration-200" style={{ color: "#818cf8", background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(99,102,241,0.18)"}
                  onMouseLeave={e => e.currentTarget.style.background = "rgba(99,102,241,0.1)"}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  Editar
                </button>
              )}
            </div>

            {/* Feedback */}
            {message.text && (
              <div className="mb-5 px-4 py-3 rounded-xl text-sm" style={message.type === "success"
                ? { background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)", color: "#86efac" }
                : { background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)", color: "#fca5a5" }}>
                {message.text}
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="dark-label">Nome</label>
                <input type="text" name="first_name" value={formData.first_name} onChange={handleInputChange} disabled={!isEditing} className="dark-input" placeholder="Seu nome" />
              </div>
              <div>
                <label className="dark-label">Sobrenome</label>
                <input type="text" name="last_name" value={formData.last_name} onChange={handleInputChange} disabled={!isEditing} className="dark-input" placeholder="Seu sobrenome" />
              </div>
              <div>
                <label className="dark-label">Usuário</label>
                <input type="text" name="username" value={formData.username} onChange={handleInputChange} disabled={!isEditing} className="dark-input" placeholder="Username" />
              </div>
              <div>
                <label className="dark-label">Email</label>
                <input type="email" name="email" value={formData.email} onChange={handleInputChange} disabled={!isEditing} className="dark-input" placeholder="seu@email.com" />
              </div>
            </div>

            {isEditing && (
              <div className="flex gap-3 mt-5">
                <button onClick={handleSave} disabled={isSaving} className="flex-1 py-2.5 rounded-xl font-medium text-sm text-white transition-all duration-200" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
                  {isSaving ? "Salvando..." : "Salvar alterações"}
                </button>
                <button onClick={handleEditToggle} disabled={isSaving} className="flex-1 py-2.5 rounded-xl font-medium text-sm transition-all duration-200" style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.5)", border: "1px solid rgba(255,255,255,0.1)" }}>
                  Cancelar
                </button>
              </div>
            )}
          </div>

          {/* Security card */}
          <div className="rounded-2xl p-6 mt-4" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white mb-0.5" style={{ fontFamily: "'Syne', sans-serif" }}>Segurança</h2>
                <p className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>Gerencie sua senha de acesso</p>
              </div>
              <button onClick={() => setIsPasswordModalOpen(true)} className="text-xs px-4 py-2 rounded-xl font-medium transition-all duration-200" style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.6)", border: "1px solid rgba(255,255,255,0.1)" }}
                onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.09)"}
                onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
              >
                Alterar senha
              </button>
            </div>
          </div>

        </div>
      </div>

      <ChangePasswordModal isOpen={isPasswordModalOpen} userId={user?.id} onClose={() => setIsPasswordModalOpen(false)} />
    </>
  );
}
