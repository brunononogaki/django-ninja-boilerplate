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
