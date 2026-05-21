import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { getSocialToken } from "utils/auth";

/**
 * Página de Callback do Google OAuth
 *
 * Fluxo:
 * 1. User clica em "Login com Google"
 * 2. Redireciona pra /accounts/google/login/
 * 3. User autentica no Google
 * 4. Google redireciona de volta pro /accounts/google/login/callback/ (Django)
 * 5. Django cria user + sessão
 * 6. Django redireciona pra LOGIN_REDIRECT_URL
 * 7. User chega nessa página com sessão Django ativa
 * 8. Essa página chama getSocialToken() pra gerar JWT
 * 9. Armazena tokens no localStorage
 * 10. Redireciona pra /home
 */
export default function GoogleCallback() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      try {
        setError("");
        setIsLoading(true);

        // Chamar endpoint pra gerar JWT usando a sessão Django
        // O backend seta os cookies httpOnly automaticamente na resposta
        await getSocialToken();

        console.log("✅ Autenticação realizada com sucesso");
        router.push("/home");
      } catch (err) {
        console.error("❌ Erro ao gerar JWT:", err);

        // Mensagem de erro mais clara
        let errorMessage = "Erro ao processar autenticação. Tente novamente.";
        if (err.message) {
          errorMessage = err.message;
        }

        setError(errorMessage);
        setIsLoading(false);
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full text-center">
        {isLoading && !error && (
          <>
            <div className="flex justify-center mb-4">
              <div className="animate-spin">
                <svg
                  className="w-12 h-12 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </div>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Processando Login
            </h1>
            <p className="text-gray-600 text-sm">
              Estamos gerando seus tokens de acesso...
            </p>
          </>
        )}

        {error && (
          <>
            <div className="flex justify-center mb-4">
              <svg
                className="w-12 h-12 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Erro na Autenticação
            </h1>
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {error}
            </div>
            <button
              onClick={() => (window.location.href = "/")}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
            >
              Voltar para Login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
