# Renovação Automática SSL com Let's Encrypt

## Configuração Atual

O site **credenshow.com.br** está configurado com certificados SSL do **Let's Encrypt** com renovação automática.

### Certificados Atuais

- **Localização:** `/etc/letsencrypt/live/credenshow.com.br/`
- **Arquivos:**
  - `fullchain.pem` - Certificado completo
  - `privkey.pem` - Chave privada

### Renovação Automática

#### Cron Job

Configurado para executar **2 vezes por dia** (às 3h e 15h):

```bash
0 3,15 * * * certbot renew --quiet --post-hook 'cd /srv/ticket_manager && docker compose restart nginx'
```

#### Deploy Hook

Quando os certificados são renovados, o hook em `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh` reinicia automaticamente o container nginx:

```bash
#!/bin/bash
cd /srv/ticket_manager && docker compose restart nginx
```

### Verificar Status

```bash
# Ver próxima execução do cron
crontab -l | grep certbot

# Testar renovação (dry-run)
certbot renew --dry-run

# Ver data de expiração dos certificados
certbot certificates
```

### Validade dos Certificados

Os certificados Let's Encrypt são válidos por **90 dias**. O certbot tenta renovar automaticamente quando faltam **30 dias** para expirar.

### Logs

- Certbot: `/var/log/letsencrypt/letsencrypt.log`
- Nginx: `docker logs ticket_manager_nginx`

## Importante

⚠️ **NUNCA modifique manualmente** os arquivos em `/etc/letsencrypt/`  
⚠️ **NÃO delete** o volume `/etc/letsencrypt` do docker-compose.yml  
⚠️ O Docker **monta os certificados como read-only** (`/etc/letsencrypt:/etc/letsencrypt:ro`)

## Forçar Renovação Manual (se necessário)

```bash
# Forçar renovação imediatamente
certbot renew --force-renewal

# Reiniciar nginx após renovação
cd /srv/ticket_manager && docker compose restart nginx
```
