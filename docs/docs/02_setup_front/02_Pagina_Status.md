# Criando a página `/status`

Essa vai ser a nossa primeira página de verdade no Front, e o objetivo dela é pegar as informações de status da nossa API e exibir na tela. Por enquanto não estamos preocupados com a formatação e nem nada disso, é só para iniciarmos alguma coisa no front-end React consumindo a API.

## Criando o arquivo da página `/status`

Primeiramente, vamos criar uma pasta chamada `status` no diretório `pages`, e criar um arquivo `index.js` lá dentro.

```bash
mkdir -p next/pages/status
touch next/pages/status/index.js
```

!!! tip

        Como o Next é file-based routing, só isso já é o suficiente para criar a página

## Iniciando o arquivo `index.js`

Vamos inicialmente criar a estrutra mais básica possível para esse arquivo, que vai nos retornar basicamente um cabeçalho escrito Status.

```javascript title="./next/pages/status/index.js"
export default function StatusPage() {
  return (
    <>
      <h1>Status</h1>
    </>
  );
}
```

Agora vamos criar uma função chamada `fetchStatus`, que faz um GET na nossa API e retorna o conteúdo. Vamos ver se rola:

```javascript title="./next/pages/status/index.js"
async function fetchStatus() {
  const response = await fetch("http://localhost:8000/api/v1/status");
  const responseBody = await response.json();
  return responseBody;
}

export default function StatusPage() {
  console.log(fetchStatus());
  return (
    <>
      <h1>Status</h1>
      <fetchStatus />
    </>
  );
}
```

!!! warning

    Ops! Não funcionou, né? Se abrirmos a console do Navegador, veremos um erro de CORS policy.

    ```
    status:1 Access to fetch at 'http://localhost:8000/api/v1/status' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
    ```

## Resolvendo erros de CORS

Para resolver esse problema de CORS, precisaremos instalar um pacote no nosso **backend** chamado `django-cors-headers`.

```bash
poetry add django-cors-headers
```

E precisamos adicionar ele nos `INSTALLED_APPS` do arquivo `./myapi/settings.py`, e criar o Middleware no mesmo arquivo:

```python title="./myapi/settings.py" hl_lines="8 21-24"
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django_extensions',
    'myapi.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # CORS
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
]
```

Agora vamos criar uma nova variável no nosso arquivo `.env.development` e `.env.production` com as origens permitidas no CORS. No caso, teremos que colocar o endereço do nosso front-end:

```bash title="./.env.development""
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

```bash title="./.env.production""
CORS_ALLOWED_ORIGINS=https://react.brunononogaki.com
```

Agora vamos voltar no nosso arquivo `./myapi/settings.py` e criar a variável `CORS_ALLOWED_ORIGINS` lá, usando o decouple para buscar o valor do .env.

```python title="./myapi/settings.py"
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://127.0.0.1:3000', cast=Csv()
)
```

!!! success

    Teste agora, e agora sim o Front vai conseguir nos mostrar os dados do retorno da API na console do navegador!

    Mas note que fizemos o GET com um simples comando `fetch`. Por enquanto, estamos dando apenas um console.log na Promise que vem como retorno da função async. Para obtermos o dado mesmo, recomenda-se ter um `Data Fetcher`.

    

## Data Fetcher

Quando realizamos um Fetch em uma API, muitas coisas erradas podem acontecer no processo. Pode dar algum erro na conexão com o backend, pode ter problema de request duplicado e cancelado, pode dar problemas de respostas não formatadas, etc. Por isso, a comunidade do React passou a desrecomendar os fetchings direto, e colocar um cara no meio para gerenciar essas requisições. Esse é o nosso `Data Fetcher`: um cara que consegue abstrair e gerenciar melhor os requests ao Backend.

Os dois módulos mais populares de Data Fetcher são:

- SWR: Criado pela Vercel
- React Query: Faz parte do TanStack, e é o módulo mais popular

E aqui nesse projeto, usaremos o `SWR`. Vamos instalá-lo como uma dependência do Next:

```bash
cd next
npm install swr
```

E para utilizá-lo, invocaremos o hook `useSWR`. Abordaremos sobre hooks do React mais pra frente, mas por hora, vamos testar esse código aqui:

```javascript title="./next/pages/status/index.js" hl_lines="1 10-12"
import useSWR from "swr";

async function fetchStatus() {
  const response = await fetch("http://localhost:8000/api/v1/status");
  const responseBody = await response.json();
  return responseBody;
}

export default function StatusPage() {
  const response = useSWR("status", fetchStatus);
  console.log(response.isLoading);
  console.log(response.data);

  return (
    <>
      <h1>Status</h1>
      <fetchStatus />
    </>
  );
}
```

!!! note

    Veja que interessante, a linha `const response = useSWR("status", fetchStatus)` não é async, ela não bloqueia a página. Conforme o useSWR executa a sua tarefa, ele pede para o React processar o componente novamente. Se colocarmos um console.log, é possível ver exatamente esse comportamento, onde ele começa com o response.isLoading como true, e com o response.data como Undefined. E logo em seguida, o response.isLoading muda para false, e o response.data tem o resultado da nossa request. Isso pode ser usado, por exemplo, para exibir uma mensagem de carregamento na tela antes de os dados da nossa API serem retornados para o Front!

    ![alt text](static/swr_1.png)

Então agora é só renderizarmos o JSON do `response.data`, e podemos colocar um refreshInterval no useSWR para ele fazer o requet a cada 2 segundos:

```javascript title="./next/pages/status/index.js"
import useSWR from "swr";

async function fetchStatus() {
  const response = await fetch("http://localhost:8000/api/v1/status");
  const responseBody = await response.json();
  return responseBody;
}

export default function StatusPage() {
  const response = useSWR("status", fetchStatus, { refreshInterval: 2000 });

  return (
    <>
      <h1>Status</h1>
      <pre>{JSON.stringify(response.data, null, 2)}</pre>
    </>
  );
}
```

!!! note

    O SWR vem com um conceito chamado `deduping`. Quando é feito um request para a nossa API usando a mesma chave (que é aquele valor "status" que passamos como primeiro parâmetro no useSWR), ele guarda na memória o retorno por 2 segundos, então se houver outra chamada igual nesse intervalo, ele retorna direto o dado que está em cache. Por isso, mesmo que a gente mude o refreshInterval para 100ms, ainda assim o refresh só ocorrerá a cada 2 segundos, que é o tempo padrão do deduping. Para alterar isso, basta passar a chave dedupingInterval, por exemplo:

    ```javascript
    const response = useSWR("status", fetchStatus, {
      refreshInterval: 100,
      dedupingInterval: 100
    });
    ```

Por fim, uma pequena refatoração para deixarmos a função fetchStatus mais genérica, recebendo o nome da chave como parâmetro. Agora podemos inclusive renomear a função para fetchAPI, porque ela pode ser usada para outras coisas, e não apenas para Status:

```javascript title="./next/pages/status/index.js"
import useSWR from "swr";

async function fetchAPI(key) {
  const response = await fetch(key);
  const responseBody = await response.json();
  return responseBody;
}

export default function StatusPage() {
  const response = useSWR("http://localhost:8000/api/v1/status", fetchAPI, {
    refreshInterval: 2000,
  });

  return (
    <>
      <h1>Status</h1>
      <pre>{JSON.stringify(response.data, null, 2)}</pre>
    </>
  );
}
```

## Pegando o endereço da API do .env

Para não deixarmos esse endereço "localhost:8000" estático no código, vamos transformá-lo em uma variável de ambiente. No Next, as variáveis de ambiente precisam ter o prefixo `NEXT_PUBLIC_` para serem acessíveis no Browser. Então lá no `.env.development`, note que já tinhamos configurado a variável `NEXT_PUBLIC_API_URL`:

```bash title="./env.development"
NEXT_PUBLIC_API_URL=localhost:8000
```

```bash title="./env.production"
NEXT_PUBLIC_API_URL=myapi.brunononogaki.com
```

E agora o Next consegue automaticamente pegar essa variável através de um `process.env.NEXT_PUBLIC_API_URL`. Por exemplo:

```javascript
  const { isLoading, data } = useSWR(
    `http://${process.env.NEXT_PUBLIC_API_URL}/api/v1/status`,
    fetchAPI,
    {
      refreshInterval: 2000,
    }
  );
```


## Trazendo as informações do Banco e refatorando a página

Agora vamos para a refatoração final, utilizando componentes responsáveis por cada pedaço da página de status para atualizar os dados do nosso Banco.

```javascript title="./next/pages/status/index.js"
import useSWR from "swr";

async function fetchAPI(key) {
  const response = await fetch(key);
  const responseBody = await response.json();
  return responseBody;
}

export default function StatusPage() {
  return (
    <>
      <h1>Status</h1>
      <UpdatedAt />
      <h2>Database</h2>
      <DatabaseStatus />
    </>
  );
}

function UpdatedAt() {
  const { isLoading, data } = useSWR(
    `http://${process.env.NEXT_PUBLIC_API_URL}/api/v1/status`,
    fetchAPI,
    {
      refreshInterval: 2000,
    }
  );
  let updatedAtText = "Carregando...";

  if (!isLoading && data) {
    updatedAtText = new Date(data.updated_at).toLocaleString("pt-BR");
  }

  return <div>Última atualização: {updatedAtText}</div>;
}

function DatabaseStatus() {
  const { isLoading, data } = useSWR(
    `http://${process.env.NEXT_PUBLIC_API_URL}/api/v1/status`,
    fetchAPI,
    {
      refreshInterval: 2000,
    }
  );
  console.log(data);
  let databaseVersion = "Carregando...";
  let databaseMaxConnctions = "Carregando...";
  let databaseOpenedConnections = "Carregando...";

  if (!isLoading && data) {
    databaseVersion = data.db_version;
    databaseMaxConnctions = data.max_connections;
    databaseOpenedConnections = data.active_connections;
  }

  return (
    <>
      <li>Database Version: {databaseVersion}</li>
      <li>Max Connections: {databaseMaxConnctions}</li>
      <li>Opened Connections: {databaseOpenedConnections}</li>
    </>
  );
}
```

!!! success

    Sucesso, temos a nossa primeira página consumindo dados da API, tratando, e exibindo na tela. Ainda tudo simples e sem formatação, mas vamos melhorando aos poucos!

    ![alt text](static/status_page_v1.png)

