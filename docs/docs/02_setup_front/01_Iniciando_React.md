# Iniciando um projeto React para o Front-end

Precisaremos de um Front-End para consumir o nosso Backend Django Ninja. Para isso, optei por criar um projeto usando `React + Vite`. Para ficar mais fácil, deixarei o código do front nesse mesmo repositório, tudo dentro da pasta `react` na raíz do projeto.

## Construindo o ambiente

### Criando a pasta do projeto do Front-End

A primeira coisa é criar a pasta `react` na raíz do projeto, e entrar nela:
```bash
mkdir -p react
cd react
```

### Definindo a versão do Node

Eu já tenho o NVM e o Node instalados, então criaremos um arquivo na pasta react chamado `.nvmrc`, onde definiremos a versão do Node que utilizaremos:

```bash title=".nvmrc"
lts/iron

```

E agora para usar essa versão, basta dar o comando:
```bash
nvm use

Now using node v20.19.6 (npm v10.8.2)
```

### Criando o projeto com o Vite

Utilizaremos o `Vite` para construir o nosso projeto, e durante o setup, escolheremos o framework `React` com `JavaScript`. Pode dar o nome que for mais conveniente, nesse exemplo vou chamar simplesmente de `myfront`:

```bash
npm create vite@latest myfront

◆  Select a framework:
│  ○ Vanilla
│  ○ Vue
│  ● React
│  ○ Preact
│  ○ Lit
│  ○ Svelte
│  ○ Solid
│  ○ Qwik
│  ○ Angular
│  ○ Marko
│  ○ Others

◆  Select a variant:
│  ○ TypeScript
│  ○ TypeScript + React Compiler
│  ○ TypeScript + SWC
│  ● JavaScript
│  ○ JavaScript + React Compiler
│  ○ JavaScript + SWC
│  ○ React Router v7 ↗
│  ○ TanStack Router ↗
│  ○ RedwoodSDK ↗
│  ○ RSC ↗
│  ○ Vike ↗
```

Esse Wizard já vai subir o nosso front no endereço http://localhost:5173, e vai criar a seguinte estrutura de pastas dentro da pasta `react`:

```bash
.
└── myfront
    ├── README.md
    ├── eslint.config.js
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── public
    │   └── vite.svg
    ├── src
    │   ├── App.css
    │   ├── App.jsx
    │   ├── assets
    │   │   └── react.svg
    │   ├── index.css
    │   └── main.jsx
    └── vite.config.js
```

