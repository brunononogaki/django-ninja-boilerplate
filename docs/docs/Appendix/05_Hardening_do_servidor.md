# Hardening do Servidor

Documentação das configurações de segurança aplicadas no servidor de produção.
Sistema operacional: Ubuntu 24.04 LTS. Ambiente: VPS com Docker + Traefik como reverse proxy.

---

## Contexto

O servidor expõe aplicações via Traefik, que escuta nas portas 80 e 443 do host. Todo o tráfego HTTP/HTTPS externo passa pela Cloudflare antes de chegar ao servidor. O acesso administrativo é feito exclusivamente via SSH com chave pública.

Antes do hardening, os principais vetores de risco eram:

- Login root por senha habilitado no SSH
- Portas 80/443 acessíveis de qualquer IP (Docker bypassa UFW por padrão)
- Sem proteção contra brute force no SSH
- Firewall (UFW) inativo
- X11Forwarding desnecessariamente habilitado

---

## 1. SSH — PermitRootLogin

**Arquivo:** `/etc/ssh/sshd_config`

### O que foi feito

```
PermitRootLogin prohibit-password
```

### Por que

O valor padrão `yes` permite login root com senha, expondo o servidor a ataques de força bruta diretos na conta mais privilegiada. A opção `prohibit-password` mantém o acesso root via chave pública (necessário para administração) e bloqueia qualquer tentativa de login com senha.

O `KbdInteractiveAuthentication no` já estava configurado, o que desabilita autenticação interativa (inclui senha). O `prohibit-password` formaliza essa restrição diretamente na conta root, independente de configurações PAM.

### Como aplicar novamente

```bash
sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sshd -t                  # valida a config antes de reiniciar
systemctl restart ssh
```

---

## 2. Docker + Cloudflare — DOCKER-USER

**Arquivos:**
- `/etc/iptables/docker-cloudflare.sh`
- `/etc/systemd/system/docker-cloudflare-iptables.service`

### O problema com Docker e firewalls

Docker gerencia suas próprias regras de iptables e **bypassa o UFW** para portas expostas. Quando um container mapeia a porta 80 do host (`0.0.0.0:80->80/tcp`), Docker adiciona regras na chain `FORWARD` que aceitam esse tráfego antes que o UFW possa bloqueá-lo.

A solução oficial do Docker para esse problema é a chain `DOCKER-USER`: ela é consultada antes de qualquer regra do Docker, e o Docker nunca a modifica — é reservada para regras do administrador.

### O que foi feito

Criado um ipset com todos os CIDRs IPv4 e IPv6 da Cloudflare, e configurada a chain `DOCKER-USER` para:

1. **ACCEPT** tráfego nas portas 80/443 vindo de IPs da Cloudflare
2. **DROP** tráfego nas portas 80/443 vindo de qualquer outro IP
3. **RETURN** para todo o resto (outras portas, tráfego interno Docker)

A correspondência usa `--ctorigdstport` do módulo `conntrack`, que captura a porta de destino **original** (antes do DNAT que o Docker aplica no PREROUTING). Sem isso, a porta vista na chain FORWARD seria a porta interna do container, não 80/443.

```
Chain DOCKER-USER
1  ACCEPT  tcp  ctorigdstport 80   match-set cloudflare-ipv4 src
2  ACCEPT  tcp  ctorigdstport 443  match-set cloudflare-ipv4 src
3  DROP    tcp  ctorigdstport 80
4  DROP    tcp  ctorigdstport 443
5  RETURN
```

O mesmo esquema foi aplicado no `ip6tables` com o ipset `cloudflare-ipv6`.

### Persistência

O Docker não toca na chain `DOCKER-USER` ao reiniciar, mas as regras de iptables são perdidas no reboot. Um serviço systemd foi criado para reaplicar tudo após o Docker subir:

```ini
# /etc/systemd/system/docker-cloudflare-iptables.service
[Unit]
After=docker.service netfilter-persistent.service
Wants=docker.service

[Service]
Type=oneshot
ExecStart=/bin/bash /etc/iptables/docker-cloudflare.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

O script é idempotente: faz flush das regras iptables antes de destruir os ipsets (necessário porque iptables mantém referência aos sets enquanto estão em uso).

### Atualizar os IPs da Cloudflare

A Cloudflare publica os ranges em:
- https://www.cloudflare.com/ips-v4
- https://www.cloudflare.com/ips-v6

Para atualizar, edite os arrays no script e rode:

```bash
bash /etc/iptables/docker-cloudflare.sh
```

---

## 3. fail2ban

**Arquivo:** `/etc/fail2ban/jail.local`

### O que foi feito

O fail2ban já vem com o jail `sshd` habilitado no Ubuntu (`/etc/fail2ban/jail.d/defaults-debian.conf`). O `jail.local` foi criado para sobrescrever os defaults com configurações mais agressivas:

```ini
[DEFAULT]
bantime           = 1h
bantime.increment = true
bantime.multiplier = 24
bantime.maxtime   = 1w
findtime          = 10m
maxretry          = 3
ignoreip          = 127.0.0.1/8 ::1

[sshd]
mode = aggressive
```

### Por que cada parâmetro

| Parâmetro | Valor | Motivo |
|-----------|-------|--------|
| `maxretry` | 3 | Default era 5; com autenticação por chave, 3 falhas já indicam ataque |
| `bantime` | 1h | Primeiro ban longo o suficiente para desincentivar |
| `bantime.increment` | true | Bans escalados para reincidentes |
| `bantime.multiplier` | 24 | 1h → 24h → ~1 mês (limitado por maxtime) |
| `bantime.maxtime` | 1w | Teto de 1 semana para não banir permanentemente por engano |
| `findtime` | 10m | Janela de observação — 3 falhas em 10 min dispara o ban |
| `mode = aggressive` | — | Detecta padrões além de falhas de senha: tentativas de auth com usuário inválido, comandos forçados, etc. |

O backend `systemd` (configurado no defaults-debian.conf) lê diretamente o journal, sem depender de arquivos de log.

O banaction padrão é `nftables` (configurado pelo Ubuntu), o que é compatível com as regras de iptables do Docker — cada um opera em sua própria camada.

### Verificar bans ativos

```bash
fail2ban-client status sshd
```

### Desbanir um IP manualmente

```bash
fail2ban-client set sshd unbanip <IP>
```

---

## 4. UFW

### O que foi feito

```bash
# /etc/default/ufw
DEFAULT_FORWARD_POLICY="ACCEPT"   # era DROP — necessário para Docker

ufw allow ssh
ufw enable
```

Resultado:

```
Default: deny (incoming), allow (outgoing), allow (routed)

22/tcp   ALLOW IN  Anywhere
22/tcp   ALLOW IN  Anywhere (v6)
```

### Por que FORWARD_POLICY="ACCEPT"

UFW gerencia a chain `INPUT` (tráfego destinado ao host) e a chain `FORWARD` (tráfego roteado). Docker também escreve regras na chain `FORWARD`. Se o UFW setasse a policy padrão do FORWARD para DROP, poderia conflitar com o roteamento interno do Docker.

Com `ACCEPT`, o UFW deixa o FORWARD para o Docker gerenciar. A segurança nas portas 80/443 já está garantida pela chain `DOCKER-USER`.

### Por que não abrir 80/443 no UFW

O UFW protege o `INPUT` — tráfego para serviços rodando **no host**. O Traefik roda **dentro de um container**: o tráfego entra pelo host, passa pelo DNAT do Docker (PREROUTING), e vai para o FORWARD. O UFW nunca vê esse tráfego no INPUT. A restrição de 80/443 é responsabilidade exclusiva do DOCKER-USER.

---

## Resumo do estado atual

| Componente | Configuração |
|------------|-------------|
| SSH root | `prohibit-password` — só chave pública |
| SSH senha interativa | Desabilitada (`KbdInteractiveAuthentication no`) |
| Portas 80/443 | Restritas a IPs da Cloudflare via `DOCKER-USER` |
| Brute force SSH | Bloqueado pelo fail2ban (ban incremental, 3 tentativas) |
| Firewall host | UFW ativo — only SSH liberado no INPUT |
| Atualizações automáticas | `unattended-upgrades` ativo |
| X11Forwarding | `no` — desabilitado |