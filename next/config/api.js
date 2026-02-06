/**
 * API Configuration
 * Centraliza todas as rotas da API Django Ninja
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const API_ENDPOINTS = {
  // Authentication endpoints
  AUTH: {
    LOGIN: "/api/v1/login",
    REFRESH: "/api/v1/refresh",
    ACTIVATE: (tokenId) => `/api/v1/users/activate/${tokenId}`,
    RESEND_ACTIVATION: (tokenId) =>
      `/api/v1/users/resend-activation/${tokenId}`,
  },

  // Users endpoints
  USERS: {
    ME: "/api/v1/me",
    LIST: "/api/v1/users",
    GET: (id) => `/api/v1/users/${id}`,
    CREATE: "/api/v1/users",
    UPDATE: (id) => `/api/v1/users/${id}`,
    DELETE: (id) => `/api/v1/users/${id}`,
    CHANGE_PASSWORD: (id) => `/api/v1/users/${id}/change-password`,
  },

  // Password Reset endpoints
  PASSWORD_RESET: {
    REQUEST: "/api/v1/users/password-reset/request",
    VALIDATE: (tokenId) => `/api/v1/users/password-reset/${tokenId}/validate`,
    CONFIRM: (tokenId) => `/api/v1/users/password-reset/${tokenId}/confirm`,
  },

  // Status endpoint
  STATUS: "/api/v1/status",
};

export default API_BASE_URL;
