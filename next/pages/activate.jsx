import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import API_BASE_URL, { API_ENDPOINTS } from "../config/api";

export default function Activate() {
  const router = useRouter();
  const { token } = router.query;
  const [status, setStatus] = useState("loading"); // loading, success, error
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;

    const activateUser = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}${API_ENDPOINTS.AUTH.ACTIVATE(token)}`,
          {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
            },
          },
        );

        if (response.ok) {
          setStatus("success");
          setMessage("Conta ativada com sucesso!");
          setTimeout(() => {
            router.push("/");
          }, 2000);
        } else {
          const data = await response.json();
          setStatus("error");
          setMessage(
            data.detail || "Erro ao ativar a conta. O link pode ter expirado.",
          );
        }
      } catch (error) {
        setStatus("error");
        setMessage("Erro ao conectar com o servidor.");
        console.error("Activation error:", error);
      }
    };

    activateUser();
  }, [token, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        {status === "loading" && (
          <>
            <div className="flex justify-center mb-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
            <h1 className="text-2xl font-bold text-gray-800 mb-2">
              Ativando sua conta...
            </h1>
            <p className="text-gray-600">
              Por favor aguarde enquanto ativamos sua conta.
            </p>
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
              Erro na ativação
            </h1>
            <p className="text-red-600 mb-4">{message}</p>
            <button
              onClick={() => router.push("/")}
              className="w-full mt-4 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition duration-200"
            >
              Voltar para o Login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
