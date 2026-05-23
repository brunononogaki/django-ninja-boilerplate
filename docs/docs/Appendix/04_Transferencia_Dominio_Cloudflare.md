# Transferindo o Domínio para a Cloudflare

## Por que usar a Cloudflare?

Quando colocamos uma aplicação em produção, o domínio precisa de um serviço de **DNS** para funcionar. O registro do domínio é feito em registradoras como Registro.br, GoDaddy ou Hostinger — mas onde você **gerencia** esse domínio faz muita diferença.

A Cloudflare oferece um plano gratuito que, além do gerenciamento de DNS, entrega uma série de funcionalidades de segurança e performance que seriam caras ou complexas de configurar por conta própria:

### Proteção contra ataques DDoS

O tráfego da sua aplicação passa pelos servidores da Cloudflare antes de chegar à sua VPS. Isso significa que ataques de negação de serviço (DDoS) são absorvidos pela infraestrutura deles, e não pela sua máquina. O IP real do seu servidor fica oculto.

### CDN (Content Delivery Network)

A Cloudflare distribui os seus assets estáticos (CSS, JS, imagens) a partir de servidores próximos ao usuário final. O resultado é uma aplicação com carregamento mais rápido, independentemente de onde o usuário esteja no mundo.

### SSL/TLS automático e gratuito

A Cloudflare emite e renova certificados SSL/TLS automaticamente para o seu domínio. Você não precisa lidar com Certbot, Let's Encrypt ou renovações manuais para o certificado público — a Cloudflare cuida disso entre o usuário e os servidores dela. A conexão entre a Cloudflare e a sua VPS pode ser configurada separadamente (modo Full ou Full Strict).

### Firewall de aplicação (WAF)

O plano gratuito inclui regras básicas de firewall que bloqueiam requisições maliciosas conhecidas antes de elas chegarem ao Django. É possível criar regras customizadas para bloquear países, IPs ou padrões de requisição.

### Gerenciamento de DNS simples e rápido

O DNS da Cloudflare é um dos mais rápidos do mundo (servidores `1.1.1.1`). Alterações de DNS propagam em segundos, não horas. A interface é limpa e fácil de usar, o que simplifica muito a configuração de subdomínios, registros MX para e-mail e outros tipos de entrada.

### Analytics e visibilidade

Mesmo no plano gratuito, você tem acesso a métricas de tráfego, ameaças bloqueadas e erros — sem precisar instalar nenhum agente na sua VPS.

---

## Passo a passo para a Transferência de Domínio

Como criamos o domínio na própria Hostinger, onde está a nossa VPS, vamos conectar esse domínio na Cloudflare.

### 1. Conectar o domínio

Na tela de domains, clique em Add Domain --> Connect a Domain:
![alt text](<static/01 - Connect a Domain.png>)

Insira o domínio desejado:
![alt text](<static/02 - Domain name.png>)

### 2. Verificando os registros DNS importados

Verifique se todos os seus registros foram importados, e se for o caso, crie os que faltam:

![alt text](<static/03 - DNS Records.png>)

### 3. Atualizando os nameservers na Hostinger

Entre na Hostinger e altere os Nameservers do seu domínio para os que foram informados pela Cloudflare:

* Cloudflare
![alt text](<static/05 - NS Cloudflare.png>)

* Hostinger:
![alt text](<static/04 - NS Hostinger.png>)

### 4. Aguardando a propagação e confirmando a ativação

Volte na tela da Cloudflare e clique no botão informando que você já fez a alteração. Aguarde a alteração ser propagada. Isso pode levar um tempo.

![alt text](<static/06 - Aguardando migracao.png>)

Mas depois de uns minutos, dê refresh na página e você verá isso:

![alt text](<static/07 - Migracao concluida.png>)

### 5. Configurando o modo SSL/TLS

A Cloudflare atua como intermediária entre o usuário e a sua VPS. Por isso, o tráfego TLS tem **dois segmentos** independentes:

```
Usuário ──[HTTPS]──► Cloudflare ──[?]──► VPS (Traefik)
```

O modo SSL/TLS controla exatamente o segundo trecho — como a Cloudflare se conecta à sua VPS. As opções são:

| Modo | O que faz | Adequado? |
|---|---|---|
| **Off** | Tudo em HTTP | Não |
| **Flexible** | Cloudflare → VPS em HTTP puro | **Não** — quebraria o Traefik, que só escuta na 443 |
| **Full** | Cloudflare → VPS em HTTPS, sem validar o certificado | Funciona, mas não ideal |
| **Full (Strict)** | Cloudflare → VPS em HTTPS, validando o certificado | **Correto** |

Como o nosso Traefik está configurado com certificados válidos do Let's Encrypt (gerados via `certbot`), o modo **Full (Strict)** é o correto. Ele garante que a Cloudflare valide o certificado antes de encaminhar o tráfego — se o cert estiver expirado ou inválido, a conexão é recusada.

Para configurar isso, entre nas configurações do seu domínio na Cloudflare, vá em SSL/TLS --> Overview e clique em Configure:

![alt text](<static/08 - Cloudflare SSL Overview.png>)

Selecione a opção Full (strict):

![alt text](<static/09 - Configure encryption mode.png>)