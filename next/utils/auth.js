/**
 * Authentication Utilities
 * Funções específicas para autenticação usando a API genérica
 */

import { apiCall } from "./api";
import API_BASE_URL, { API_ENDPOINTS } from "config/api";

/**
 * Fazer login com usuário e senha
 * O backend seta os cookies httpOnly automaticamente na resposta
 *
 * @param {string} username
 * @param {string} password
 */
export async function loginUser(username, password) {
  await apiCall(API_ENDPOINTS.AUTH.LOGIN, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

/**
 * Criar uma nova conta de usuário
 */
export async function signupUser(username, email, password, firstName, lastName) {
  return await apiCall(API_ENDPOINTS.USERS.CREATE, {
    method: "POST",
    body: JSON.stringify({
      username,
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    }),
  });
}

/**
 * Ativar conta do usuário usando token de ativação
 */
export async function activateUser(tokenId) {
  return await apiCall(API_ENDPOINTS.AUTH.ACTIVATE(tokenId), {
    method: "PATCH",
  });
}

/**
 * Fazer logout
 * Com cookies httpOnly, o JS não consegue deletá-los diretamente —
 * precisamos chamar o backend para limpar os cookies
 */
export async function logoutUser() {
  try {
    await apiCall(API_ENDPOINTS.AUTH.LOGOUT, { method: "POST" });
  } catch (err) {
    console.error("Erro ao fazer logout:", err);
  }
}

/**
 * Verificar se usuário está autenticado
 * Lê o cookie is_logged_in — ele não é httpOnly, então o JS consegue ler
 * Ele não contém o token em si, só indica se existe uma sessão ativa
 *
 * @returns {boolean}
 */
export function isAuthenticated() {
  if (typeof document === "undefined") return false; // SSR safety
  return document.cookie.split(";").some((c) => c.trim().startsWith("is_logged_in="));
}

/**
 * Atualizar access token usando refresh token
 * O refresh_token chega ao backend via cookie automaticamente —
 * não precisamos mais enviá-lo no body
 */
export async function refreshAccessToken() {
  await apiCall(API_ENDPOINTS.AUTH.REFRESH, { method: "POST" });
}

/**
 * Iniciar login com Google
 */
export function loginWithGoogle() {
  const googleAuthUrl = `${API_BASE_URL}${API_ENDPOINTS.SOCIAL_AUTH.GOOGLE_LOGIN}`;
  window.location.href = googleAuthUrl;
}

/**
 * Obter token JWT após autenticação OAuth
 * O backend seta os cookies automaticamente na resposta
 */
export async function getSocialToken() {
  await apiCall(API_ENDPOINTS.AUTH.SOCIAL_TOKEN, { method: "POST" });
}
