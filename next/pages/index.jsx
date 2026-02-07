import { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import { loginUser, loginWithGoogle } from "utils/auth";
import { requestPasswordReset } from "utils/users";

/**
 * Modal de Recuperação de Senha
 * Permite ao usuário solicitar um link de reset de senha via email
 */
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

      setMessage(
        response.message || "Verifique seu email para resetar a senha",
      );
      setEmail("");

      // Fechar modal após 3 segundos
      setTimeout(() => {
        onClose();
        setMessage("");
      }, 3000);
    } catch (err) {
      setMessage("Erro ao solicitar reset de senha. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setMessage("");
    setEmail("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Recuperar Senha
        </h2>
        <p className="text-gray-600 mb-6 text-sm">
          Digite seu email e enviaremos um link para resetar sua senha.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Mensagem de Feedback */}
          {message && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
              {message}
            </div>
          )}

          {/* Campo Email */}
          <div>
            <label
              htmlFor="forgotPasswordEmail"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Email
            </label>
            <input
              id="forgotPasswordEmail"
              type="email"
              placeholder="seu.email@exemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Botões */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-900 font-semibold py-2 px-4 rounded-lg transition duration-200"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-2 px-4 rounded-lg transition duration-200 disabled:cursor-not-allowed"
            >
              {isLoading ? "Enviando..." : "Enviar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isForgotPasswordModalOpen, setIsForgotPasswordModalOpen] =
    useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await loginUser(username, password);

      // Verificar se houve erro (status_code presente)
      if (response.status_code && response.status_code !== 200) {
        setError(response.message || "Erro ao fazer login");
        setIsLoading(false);
        return;
      }

      // Se o login foi bem-sucedido, redireciona para home
      router.push("/home");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          Login
        </h1>
        <p className="text-gray-600 mb-8 text-center">
          Django Ninja Boilerplate
        </p>

        <form onSubmit={handleLogin} className="space-y-5">
          {/* Mensagem de Erro */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Campo Username */}
          <div>
            <label
              htmlFor="username"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Usuário
            </label>
            <input
              id="username"
              type="text"
              placeholder="Digite seu usuário"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Campo Senha */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Senha
            </label>
            <input
              id="password"
              type="password"
              placeholder="Digite sua senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
          </div>

          {/* Botão Login */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-2 px-4 rounded-lg transition duration-200 disabled:cursor-not-allowed"
          >
            {isLoading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        {/* Social Login */}
        <div className="mt-6 space-y-4">
          <p className="text-center text-gray-600 text-sm">ou entre com</p>
          <button
            type="button"
            onClick={loginWithGoogle}
            className="w-full bg-white hover:bg-gray-50 text-gray-700 font-semibold py-2 px-4 rounded-lg transition duration-200 border border-gray-300 flex items-center justify-center gap-3"
          >
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
              <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
              <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"/>
              <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
            </svg>
            Continuar com Google
          </button>
        </div>

        {/* Link para Signup e Esqueci Senha */}
        <div className="mt-6 space-y-3 text-center">
          <p className="text-gray-600 text-sm">
            Não tem uma conta?{" "}
            <Link
              href="/registration"
              className="text-blue-600 hover:text-blue-700 font-semibold underline"
            >
              Crie sua conta
            </Link>
          </p>
          <button
            type="button"
            onClick={() => setIsForgotPasswordModalOpen(true)}
            className="text-blue-600 hover:text-blue-700 text-sm font-semibold underline w-full"
          >
            Esqueci minha senha
          </button>
        </div>

        {/* Modal Esqueci Senha */}
        <ForgotPasswordModal
          isOpen={isForgotPasswordModalOpen}
          onClose={() => setIsForgotPasswordModalOpen(false)}
        />
      </div>
    </div>
  );
}
