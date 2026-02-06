import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { validatePasswordReset, confirmPasswordReset } from "utils/users";

export default function ResetPassword() {
  const router = useRouter();
  const { token_id } = router.query;
  const [status, setStatus] = useState("loading"); // loading, form, success, error
  const [message, setMessage] = useState("");

  const [formData, setFormData] = useState({
    newPassword: "",
    confirmPassword: "",
  });

  const [formError, setFormError] = useState("");

  // Validar token ao carregar a página
  useEffect(() => {
    if (!token_id) return;

    const validateToken = async () => {
      try {
        const result = await validatePasswordReset(token_id);
        if (result.valid) {
          setStatus("form");
        } else {
          setStatus("error");
          setMessage(result.message || "Link inválido ou expirado");
        }
      } catch (error) {
        setStatus("error");
        setMessage("Erro ao conectar com o servidor.");
        console.error("Validation error:", error);
      }
    };

    validateToken();
  }, [token_id]);

  // Validar força da senha
  const validatePassword = (password) => {
    if (password.length < 8) {
      return "A senha deve ter no mínimo 8 caracteres";
    }
    return "";
  };

  // Manipular mudanças no formulário
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Limpar erro ao usuário começar a digitar
    if (formError) {
      setFormError("");
    }
  };

  // Submeter formulário
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validações
    const passwordError = validatePassword(formData.newPassword);
    if (passwordError) {
      setFormError(passwordError);
      return;
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setFormError("As senhas não correspondem");
      return;
    }

    setStatus("loading");

    try {
      await confirmPasswordReset(token_id, formData.newPassword);
      setStatus("success");
      setMessage("Senha redefinida com sucesso!");

      // Redirecionar para login após 2 segundos
      setTimeout(() => {
        router.push("/");
      }, 2000);
    } catch (error) {
      setStatus("form");
      setFormError(
        error.message || "Erro ao redefinir senha. Tente novamente.",
      );
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        {status === "loading" && (
          <>
            <div className="flex justify-center mb-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Validando link...
            </h1>
            <p className="text-gray-600">
              Por favor aguarde enquanto validamos seu link de reset.
            </p>
          </>
        )}

        {status === "form" && (
          <>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Redefinir Senha
            </h1>
            <p className="text-gray-600 mb-6">Digite sua nova senha abaixo</p>

            {formError && (
              <div className="mb-4 bg-red-100 rounded-lg p-3">
                <p className="text-red-600 text-sm">{formError}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-left">
              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Nova Senha
                </label>
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  required
                  value={formData.newPassword}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Mínimo 8 caracteres"
                />
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Confirmar Senha
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Confirme sua nova senha"
                />
              </div>

              <button
                type="submit"
                className="w-full mt-6 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition duration-200"
              >
                Redefinir Senha
              </button>
            </form>

            <div className="mt-4 text-center">
              <button
                onClick={() => router.push("/")}
                className="text-sm text-blue-500 hover:text-blue-600 transition duration-200"
              >
                Voltar para o Login
              </button>
            </div>
          </>
        )}

        {status === "success" && (
          <>
            <div className="flex justify-center mb-4">
              <div className="bg-green-100 rounded-full p-3">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Sucesso!</h1>
            <p className="text-green-600 mb-4">{message}</p>
            <p className="text-gray-600 text-sm">
              Redirecionando para o login...
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="flex justify-center mb-4">
              <div className="bg-red-100 rounded-full p-3">
                <svg
                  className="w-8 h-8 text-red-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Link Inválido ou Expirado
            </h1>
            <p className="text-red-600 mb-6">{message}</p>
            <button
              onClick={() => router.push("/")}
              className="w-full mt-4 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition duration-200"
            >
              Voltar para o Login
            </button>
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-600">
                Você pode solicitar um novo link de reset na página de login.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
