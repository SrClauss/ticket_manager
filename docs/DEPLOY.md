# 🚀 Guia de Deploy - Ticket Manager com Editor React

## TL;DR - Deploy Rápido

```bash
# Opção 1: Script automatizado (mais fácil)
./scripts/deploy_production.sh

# Opção 2: Docker (recomendado para produção)
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 📦 Opção 1: Deploy Manual (VM/VPS)

### Pré-requisitos
- Python 3.11+
- Node.js 18+
- MongoDB 7+
- Nginx (opcional, mas recomendado)

### Passo a Passo

```bash
# 1. Clone o repositório
git clone <seu-repo>
cd ticket_manager

# 2. Execute o script de deploy
chmod +x scripts/deploy_production.sh
./scripts/deploy_production.sh

# 3. Configure variáveis de ambiente
cat > .env << EOF
MONGODB_URL=mongodb://admin:password@localhost:27017
DATABASE_NAME=ticket_manager
ENV=production
JWT_SECRET=seu_secret_muito_seguro_aqui
EOF

# 4. Inicie a aplicação
# Com uvicorn (desenvolvimento)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Com Gunicorn (produção)
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Systemd Service (Linux)

Crie `/etc/systemd/system/ticket-manager.service`:

```ini
[Unit]
Description=Ticket Manager API
After=network.target mongodb.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ticket_manager
Environment="PATH=/opt/ticket_manager/.venv/bin"
ExecStart=/opt/ticket_manager/.venv/bin/gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ative:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ticket-manager
sudo systemctl start ticket-manager
sudo systemctl status ticket-manager
```

---

## 🐳 Opção 2: Deploy com Docker (RECOMENDADO)

### Build e Run

```bash
# 1. Build da imagem
docker build -f Dockerfile.prod -t ticket-manager:latest .

# 2. Ou use docker-compose (mais fácil)
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Verifique os logs
docker-compose -f docker-compose.prod.yml logs -f app

# 4. Acesse
http://seu-servidor:8000
```

### Comandos Úteis

```bash
# Parar tudo
docker-compose -f docker-compose.prod.yml down

# Rebuild apenas o app (sem cache)
docker-compose -f docker-compose.prod.yml build --no-cache app

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Backup do MongoDB
docker exec ticket_manager_mongo_prod mongodump --out=/dump
docker cp ticket_manager_mongo_prod:/dump ./backup-$(date +%Y%m%d)

# Restore
docker cp ./backup ticket_manager_mongo_prod:/dump
docker exec ticket_manager_mongo_prod mongorestore /dump
```

---

## 🌐 Nginx (Reverse Proxy)

Se não usar docker-compose com nginx incluído, configure manualmente:

```nginx
# /etc/nginx/sites-available/ticket-manager
server {
    listen 80;
    server_name seu-dominio.com;
    client_max_body_size 20M;

    location /static/editor/ {
        proxy_pass http://127.0.0.1:8000;
        add_header Cache-Control "public, max-age=86400";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative:
```bash
sudo ln -s /etc/nginx/sites-available/ticket-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL com Certbot (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

---

## 🔧 Configuração de Produção

### Variáveis de Ambiente

Crie `.env` na raiz do projeto:

```env
# MongoDB
MONGODB_URL=mongodb://admin:SecurePassword123@localhost:27017
DATABASE_NAME=ticket_manager

# Aplicação
ENV=production
DEBUG=false

# Segurança
JWT_SECRET=sua_chave_jwt_super_secreta_mude_isso
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Admin Inicial
ADMIN_USERNAME=admin
ADMIN_PASSWORD=MudeIstoEmProducao123!
ADMIN_EMAIL=admin@seudominio.com
```

### Checklist de Segurança

- [ ] Trocar todas as senhas padrão
- [ ] Configurar firewall (liberar apenas portas 80, 443, 22)
- [ ] Habilitar SSL/TLS
- [ ] Configurar backup automático do MongoDB
- [ ] Limitar rate limiting no Nginx
- [ ] Configurar monitoramento (opcional: PM2, Supervisor)
- [ ] Revisar permissões de arquivos (`chmod`, `chown`)
- [ ] Configurar logs rotation

---

## 📊 Monitoramento

### Healthcheck

```bash
# Verifica se API está respondendo
curl http://localhost:8000/docs

# Verifica MongoDB
docker exec ticket_manager_mongo_prod mongosh --eval "db.adminCommand('ping')"
```

### Logs

```bash
# Systemd
sudo journalctl -u ticket-manager -f

# Docker
docker-compose -f docker-compose.prod.yml logs -f app

# Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## 🔄 Atualizações

### Atualizar Aplicação

```bash
# 1. Puxe as mudanças
git pull origin main

# 2. Rebuild do editor
./scripts/deploy_production.sh

# 3. Reinicie o serviço
# Systemd:
sudo systemctl restart ticket-manager

# Docker:
docker-compose -f docker-compose.prod.yml up -d --build app
```

### Atualizar Apenas o Editor React

```bash
cd editor-de-layout-de
npm run build
cd ..
rm -rf app/static/editor
cp -r editor-de-layout-de/dist app/static/editor/

# Não precisa reiniciar - arquivos estáticos são servidos diretamente
```

---

## 🆘 Troubleshooting

### Editor não carrega

```bash
# Verifica se arquivos foram copiados
ls -la app/static/editor/

# Deve ter: index.html, assets/, etc
```

### API retorna 500

```bash
# Verifica logs
sudo journalctl -u ticket-manager -n 50

# Testa conexão com MongoDB
mongosh "mongodb://admin:password@localhost:27017"
```

### Porta já em uso

```bash
# Descobre o que está usando a porta
sudo lsof -i :8000

# Mata o processo
sudo kill -9 <PID>
```

---

## 📈 Performance

### Otimizações Recomendadas

1. **Gunicorn com múltiplos workers**
   ```bash
   # Regra: (2 x num_cores) + 1
   gunicorn app.main:app -w 9 -k uvicorn.workers.UvicornWorker
   ```

2. **MongoDB indexes** (já criados automaticamente via `create_indexes()`)

3. **Nginx caching**
   ```nginx
   proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m;
   location /static/ {
       proxy_cache my_cache;
   }
   ```

4. **CDN para estáticos** (opcional)
   - Upload `app/static/editor/` para CDN (Cloudflare, AWS CloudFront)
   - Atualizar `editor_layout.html` para usar URL do CDN

---

## 📝 Resumo

| Método | Dificuldade | Tempo | Recomendado |
|--------|-------------|-------|-------------|
| Script deploy | ⭐⭐ | 5 min | Dev/Teste |
| Docker Compose | ⭐⭐⭐ | 10 min | ✅ Produção |
| Manual + Systemd | ⭐⭐⭐⭐ | 30 min | VPS dedicada |

**Recomendação**: Use Docker Compose para produção. É isolado, reproduzível e fácil de gerenciar.

---

## 🎯 Quick Start Production

```bash
# 1. Clone
git clone <repo>
cd ticket_manager

# 2. Configure
cp .env.example .env
nano .env  # Edite as senhas

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Acesse
http://seu-servidor

# 5. Login
admin / (senha do .env)
```

**Pronto!** 🚀
