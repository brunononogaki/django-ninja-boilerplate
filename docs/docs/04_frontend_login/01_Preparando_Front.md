# Preparando o Front-End para a tela de login

Por enquanto o nosso front-end só tem uma página de status e uma página inicial fake que criamos para testar o `Tailwind CSS`. Agora vamos começar a pensar na estrutura que teremos nele para se comunicar com o nosso backend.

## Estrutura de pastas

A estrutura de pastas definida para esse projeto seguirá essa lógica:

```bash
next/
├── config/
│   └── api.js                    ← Todas as rotas API
├── utils/
│   ├── api.js                    ← Fetch genérico
│   └── auth.js                   ← Lógica de auth
├── hooks/
│   ├── useAuth.js
│   └── useUsers.js
├── components/
│   ├── Auth/
│   │   ├── LoginForm.js
│   │   └── SignupForm.js
│   └── Common/
│       ├── Header.js
│       ├── Sidebar.js
│       └── Footer.js
├── pages/
│   ├── index.js                  ← Home/Login
│   └── users/
│       ├── index.js              ← Perfil
│       └── settings.js           ← Configurações
├── styles/
│   └── globals.css
└── public/
    ├── favicon.ico
    └── logo.png
```

Na pasta `config`, teremos um arquivo `api.js`, que centralizará a declaração de todas as rotas da nossa API. Assim, todos os endpoints que o front utilizar estarão num único lugar, facilitando manutenção e mudanças.

Na pasta `utils`, teremos funções reutilizáveis de baixo nível:

- `api.js` - Fetch genérico com tratamento de erros centralizados
- `auth.js` - Funções de autenticação (login, signup, logout) que consomem as rotas do `config/api.js`

Na pasta `hooks`, teremos custom hooks React que encapsulam a lógica de estado e UI:

- `useAuth.js` - Hook que gerencia autenticação (usuário logado, token, etc)
  Esses hooks usam as funções de `utils/` para buscar dados e gerenciam o estado da aplicação.

Na pasta `components`, teremos componentes reutilizáveis organizados por feature:

- `Auth/` - LoginForm.js, SignupForm.js (componentes que usam `useAuth()`)
- `Common/` - Header, Sidebar, Footer (componentes compartilhados)

## Arquivo `config/api.js`

Começando com o arquivo de declaração das nossas rotas, será basicamente um JSON que vamos exportar na variável `API_ENDPINTS`, onde teremos todos os endpoints da API. Esse arquivo estará em constante evolução conforme o projeto for crescendo:

```javascript title="./next/config/api.js"
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

  // Status endpoint
  STATUS: "/api/v1/status",
};

export default API_BASE_URL;
```

!!! note

    Veja que aqui usamos uma funcionalidade do Next.js que carrega automaticamente as variáveis do `.env.development` ou `.env.production`.

    Mas atenção: no Next.js, **apenas variáveis com o prefixo `NEXT_PUBLIC_` são expostas para o browser**. Variáveis sem esse prefixo só funcionam no servidor (Node.js). Por isso usamos `process.env.NEXT_PUBLIC_API_URL` - ela fica disponível no código React que roda no navegador.

    Essas variáveis são injetadas em **tempo de build**, então qualquer mudança no `.env` requer rebuild da aplicação.

## Arquivo `utils/api.js`

Nesse arquivo teremos um fetch genérico para a API, com uma função chamada `apiCall()`. A ideia é que quando precisarmos fazer um fetch em uma API, possamos fazer da seguinte forma:

```javascript
apiCall("/api/v1/login", {
  method: "POST",
  body: JSON.stringify({ username, password }),
});
```

E essa função já injetará o JWT Token no header, fará o request para o backend e devolverá o retorno do back. Futuramente podemos adicionar mais lógica nessa função, mas por enquanto podemos deixar assim bem simples. O arquivo ficará assim:

```javascript title=".next/utils/api.js"
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
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Se a resposta for vazia (204 No Content), retornar null
  if (response.status === 204) {
    return null;
  }

  // Parsear JSON
  const data = await response.json();

  // Retornar dados sempre, sem importar se foi sucesso ou erro
  return data;
}
```

## Arquivo `utils/auth.js`

Esse arquivo é específico para o sistema de autenticação e cadastro, e conterá a lógica para fazer o login, refresh do token, cadastro e ativação do usuário.

No futuro, quando tivermos outras aplicações, teremos que criar novos arquivos. Por exemplo, se esse app se tornar uma plataforma de armazenamento de receitas, teríamos aqui um arquivo `receipes.js`, com as lógicas de criar, ler, apagar e atualizar as receitas.

```javascript title="./next/utils/auth.js"
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
```

!!! success

    Pronto, já temos a base do nosso front pronta para fazer consultas na nossa API Django Ninja! Vamos começar a construir a nossa página em cima dessa estrutura.
