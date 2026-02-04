import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { getToken, logoutUser, getCurrentUser } from "utils/auth";

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Verifica se o usuário está autenticado
    if (!getToken()) {
      router.push("/");
      return;
    }

    // Busca dados do usuário autenticado
    const fetchUser = async () => {
      try {
        const userData = await getCurrentUser();

        // Verificar se houve erro
        if (userData.status_code && userData.status_code !== 200) {
          logoutUser();
          router.push("/");
          return;
        }

        setUser(userData);
      } catch (error) {
        console.error("Erro ao buscar dados do usuário:", error);
        logoutUser();
        router.push("/");
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  const handleLogout = () => {
    logoutUser();
    router.push("/");
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
        <div className="text-white text-center">
          <p className="text-xl">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md w-full text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Olá, {user?.username || "Usuário"}!
        </h1>
        <p className="text-gray-600 mb-8 text-lg">
          Bem-vindo ao Django Ninja Boilerplate
        </p>

        <button
          onClick={handleLogout}
          className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
        >
          Sair
        </button>
      </div>
    </div>
  );
}
