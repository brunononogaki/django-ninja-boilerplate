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
