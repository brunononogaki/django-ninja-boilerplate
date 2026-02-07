/**
 * Generic API Call Handler
 * Centraliza requisições HTTP com tratamento de erros e autenticação
 */

import API_BASE_URL from "config/api";

/**
 * Função genérica para fazer requisições à API
 * Automaticamente adiciona token JWT se existir
 *
 * @param {string} endpoint - Endpoint da API (ex: '/api/v1/login')
 * @param {object} options - Opções do fetch (method, body, headers, etc)
 * @returns {Promise} - Resposta da API em JSON
 *
 * @example
 * // GET
 * const user = await apiCall('/api/v1/users/me');
 *
 * // POST
 * const data = await apiCall('/api/v1/login', {
 *   method: 'POST',
 *   body: JSON.stringify({ username, password }),
 * });
 */
export async function apiCall(endpoint, options = {}) {
  // Construir URL completa
  const url = `${API_BASE_URL}${endpoint}`;

  // Preparar headers padrão
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // Adicionar token JWT se existir
  const token = localStorage.getItem("access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Fazer requisição
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err) {
    console.error(`Erro de conexão ao fazer requisição para ${url}:`, err);
    throw new Error(`Erro de conexão: ${err.message}`);
  }

  // Se a resposta for vazia (204 No Content), retornar null
  if (response.status === 204) {
    return null;
  }

  // Parsear JSON
  let data;
  try {
    data = await response.json();
  } catch (err) {
    console.error(`Erro ao fazer parse de JSON da resposta de ${url}:`, err);
    throw new Error(`Erro ao processar resposta: ${response.statusText}`);
  }

  // Se não foi sucesso (2xx), lançar erro com detalhes
  if (!response.ok) {
    const errorMessage = data?.message || response.statusText;
    console.error(`Erro ${response.status} em ${url}:`, data);
    throw new Error(`Erro ${response.status}: ${errorMessage}`);
  }

  // Retornar dados se foi sucesso
  return data;
}
