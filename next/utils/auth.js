/**
 * Authentication Utilities
 * Funções específicas para autenticação usando a API genérica
 */

import { apiCall } from "./api";
import API_BASE_URL, { API_ENDPOINTS } from "config/api";

/**
 * Fazer login com usuário e senha
 * Retorna access_token que é salvo no localStorage
 *
 * @param {string} username - Nome de usuário ou email
 * @param {string} password - Senha
 * @returns {Promise} - Resposta com access_token
 *
 * @example
 * const response = await loginUser('bruno', 'senha123');
 * // { access_token: '...', user: {...} }
 */
export async function loginUser(username, password) {
  const endpoint = `${API_BASE_URL}${API_ENDPOINTS.AUTH.LOGIN}`;

  const response = await apiCall(API_ENDPOINTS.AUTH.LOGIN, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  // Salvar tokens no localStorage
  if (response.access_token) {
    localStorage.setItem("access_token", response.access_token);
  }
  if (response.refresh_token) {
    localStorage.setItem("refresh_token", response.refresh_token);
  }

  return response;
}

/**
 * Criar uma nova conta de usuário
 * Envia email de ativação para o usuário
 *
 * @param {string} username - Nome de usuário
 * @param {string} email - Email do usuário
 * @param {string} password - Senha
 * @param {string} firstName - Primeiro nome
 * @param {string} lastName - Sobrenome
 * @returns {Promise} - Resposta com dados do usuário criado
 *
 * @example
 * const user = await signupUser('bruno', 'bruno@email.com', 'senha123', 'Bruno', 'Nonogaki');
 * // { id: '...', username: 'bruno', email: 'bruno@email.com', first_name: 'Bruno', last_name: 'Nonogaki' }
 */
export async function signupUser(username, email, password, firstName, lastName) {
  const response = await apiCall(API_ENDPOINTS.USERS.CREATE, {
    method: "POST",
    body: JSON.stringify({ 
      username, 
      email, 
      password,
      first_name: firstName,
      last_name: lastName,
    }),
  });

  return response;
}

/**
 * Ativar conta do usuário usando token de ativação
 * O token é enviado por email ao usuário
 *
 * @param {string} tokenId - ID do token de ativação
 * @returns {Promise} - Resposta com status de ativação
 *
 * @example
 * const result = await activateUser('d89c6ae1-adb2-4df3-956e-3e68d840c3eb');
 * // { message: 'Conta ativada com sucesso' }
 */
export async function activateUser(tokenId) {
  const endpoint = API_ENDPOINTS.AUTH.ACTIVATE(tokenId);

  const response = await apiCall(endpoint, {
    method: "PATCH",
  });

  return response;
}

/**
 * Fazer logout
 * Remove tokens do localStorage
 *
 * @example
 * logoutUser();
 */
export function logoutUser() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

/**
 * Verificar se usuário está autenticado
 * Verifica se há token no localStorage
 *
 * @returns {boolean}
 *
 * @example
 * if (isAuthenticated()) {
 *   // Usuário logado
 * }
 */
export function isAuthenticated() {
  return !!localStorage.getItem("access_token");
}

/**
 * Pegar token JWT armazenado
 *
 * @returns {string|null}
 */
export function getToken() {
  return localStorage.getItem("access_token");
}

/**
 * Atualizar access token usando refresh token
 * Gera um novo access_token mantendo a sessão ativa
 *
 * @param {string} refreshToken - Refresh token armazenado
 * @returns {Promise} - Resposta com novo access_token
 *
 * @example
 * const response = await refreshAccessToken(localStorage.getItem('refresh_token'));
 * // { access_token: '...', refresh_token: '...' }
 */
export async function refreshAccessToken(refreshToken) {
  if (!refreshToken) {
    throw new Error("No refresh token provided");
  }

  const response = await apiCall(API_ENDPOINTS.AUTH.REFRESH, {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  // Atualizar tokens no localStorage
  if (response.access_token) {
    localStorage.setItem("access_token", response.access_token);
  }
  if (response.refresh_token) {
    localStorage.setItem("refresh_token", response.refresh_token);
  }

  return response;
}

/**
 * Buscar dados do usuário autenticado
 * Usa o token armazenado para buscar os dados do usuário logado
 *
 * @returns {Promise} - Resposta com dados do usuário
 *
 * @example
 * const user = await getCurrentUser();
 * // { id: '...', username: 'bruno', email: 'bruno@email.com', ... }
 */
export async function getCurrentUser() {
  const response = await apiCall(API_ENDPOINTS.USERS.ME, {
    method: "GET",
  });

  return response;
}
