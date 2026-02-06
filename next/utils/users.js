/**
 * User Utilities
 * Funções para gerenciar dados de usuários usando a API genérica
 */

import { apiCall } from "./api";
import { API_ENDPOINTS } from "config/api";

/**
 * Obter dados do usuário atual autenticado
 * Requer token JWT válido
 *
 * @returns {Promise} - Dados do usuário autenticado
 *
 * @example
 * const user = await getCurrentUser();
 * // { id: '...', username: 'bruno', email: 'bruno@email.com', first_name: 'Bruno', last_name: 'Nonogaki', is_active: true }
 */
export async function getCurrentUser() {
  const response = await apiCall(API_ENDPOINTS.USERS.ME, {
    method: "GET",
  });

  return response;
}

/**
 * Atualizar dados do usuário
 * Pode atualizar: username, first_name, last_name, email
 * Requer token JWT válido e permissão (owner ou admin)
 *
 * @param {string} userId - ID do usuário
 * @param {Object} userData - Objeto com dados a atualizar
 * @param {string} userData.username - (opcional) Novo nome de usuário
 * @param {string} userData.first_name - (opcional) Novo primeiro nome
 * @param {string} userData.last_name - (opcional) Novo sobrenome
 * @param {string} userData.email - (opcional) Novo email
 * @returns {Promise} - Dados do usuário atualizado
 *
 * @example
 * const updated = await updateUser('user-id-123', {
 *   first_name: 'João',
 *   last_name: 'Silva'
 * });
 * // { id: '...', username: 'bruno', first_name: 'João', last_name: 'Silva', ... }
 */
export async function updateUser(userId, userData) {
  const endpoint = API_ENDPOINTS.USERS.UPDATE(userId);

  const response = await apiCall(endpoint, {
    method: "PATCH",
    body: JSON.stringify(userData),
  });

  return response;
}

/**
 * Alterar senha do usuário
 * Requer senha atual para verificação
 * Requer token JWT válido
 *
 * @param {string} userId - ID do usuário
 * @param {string} currentPassword - Senha atual
 * @param {string} newPassword - Nova senha
 * @returns {Promise} - Resposta com status
 *
 * @example
 * const result = await changeUserPassword('user-id-123', 'senhaAtual123', 'novaSenha456');
 * // { message: 'Senha alterada com sucesso' }
 */
export async function changeUserPassword(userId, currentPassword, newPassword) {
  const endpoint = API_ENDPOINTS.USERS.CHANGE_PASSWORD(userId);

  const response = await apiCall(endpoint, {
    method: "PATCH",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });

  return response;
}

/**
 * Obter usuário por ID
 * Requer permissão apropriada
 *
 * @param {string} userId - ID do usuário
 * @returns {Promise} - Dados do usuário
 *
 * @example
 * const user = await getUserById('user-id-123');
 */
export async function getUserById(userId) {
  const endpoint = API_ENDPOINTS.USERS.GET(userId);

  const response = await apiCall(endpoint, {
    method: "GET",
  });

  return response;
}

/**
 * Deletar usuário
 * Requer permissão apropriada (owner ou admin)
 *
 * @param {string} userId - ID do usuário
 * @returns {Promise} - Resposta com status
 *
 * @example
 * const result = await deleteUser('user-id-123');
 */
export async function deleteUser(userId) {
  const endpoint = API_ENDPOINTS.USERS.DELETE(userId);

  const response = await apiCall(endpoint, {
    method: "DELETE",
  });

  return response;
}

/**
 * Solicitar reset de senha
 * Envia email com link de reset para o usuário
 * Não requer autenticação (endpoint público)
 *
 * @param {string} email - Email do usuário
 * @returns {Promise} - Resposta com mensagem de sucesso
 *
 * @example
 * const result = await requestPasswordReset('usuario@email.com');
 * // { message: 'If email exists, a reset link will be sent' }
 */
export async function requestPasswordReset(email) {
  const response = await apiCall(API_ENDPOINTS.PASSWORD_RESET.REQUEST, {
    method: "POST",
    body: JSON.stringify({ email }),
  });

  return response;
}

/**
 * Confirmar reset de senha
 * Altera a senha usando o token de reset enviado por email
 * Não requer autenticação (endpoint público)
 *
 * @param {string} tokenId - ID do token de reset (UUID)
 * @param {string} newPassword - Nova senha
 * @returns {Promise} - Resposta com mensagem de sucesso
 *
 * @example
 * const result = await confirmPasswordReset('token-uuid-123', 'novaSenha456');
 * // { message: 'Password changed successfully' }
 */
export async function confirmPasswordReset(tokenId, newPassword) {
  const endpoint = API_ENDPOINTS.PASSWORD_RESET.CONFIRM(tokenId);

  const response = await apiCall(endpoint, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword }),
  });

  return response;
}

/**
 * Validar token de reset de senha
 * Verifica se o token é válido, não expirado e ainda não foi usado
 * Não requer autenticação (endpoint público)
 *
 * @param {string} tokenId - ID do token de reset (UUID)
 * @returns {Promise} - Objeto com valid (boolean) e message (string)
 *
 * @example
 * const result = await validatePasswordReset('token-uuid-123');
 * // { valid: true, message: 'Token is valid' }
 * // ou
 * // { valid: false, message: 'Token has expired' }
 */
export async function validatePasswordReset(tokenId) {
  const endpoint = API_ENDPOINTS.PASSWORD_RESET.VALIDATE(tokenId);

  const response = await apiCall(endpoint, {
    method: "GET",
  });

  return response;
}
