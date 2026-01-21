# Correção do Problema de Autenticação MongoDB / MongoDB Authentication Fix

## English Summary

**Problem**: Authentication errors occurred when trying to login with default admin credentials after starting containers, even after deleting all volumes.

**Root Cause**: The MongoDB connection URL in `docker-compose.yml` was missing the `authSource=admin` parameter, which is required to authenticate against MongoDB's admin database where root users are created.

**Solution**: Added `?authSource=admin` to the MONGODB_URL in both `docker-compose.yml` and `docker-compose.dev.yml`.

**Default Credentials**:
- Username: `admin`
- Password: `admin_key_change_in_production`

**Testing**: After applying the fix, run `docker compose down -v && docker compose up --build -d` and login at http://localhost:8000/admin/login

---

## Problema
Ao iniciar os containers com `docker compose up`, ocorria erro de autenticação ao tentar fazer login com as credenciais padrão do administrador, mesmo após deletar todos os volumes e reconstruir os containers.

## Causa Raiz
O URL de conexão do MongoDB no `docker-compose.yml` estava faltando o parâmetro `authSource=admin`, que é necessário para que o MongoDB saiba qual banco de dados usar para autenticar o usuário.

### Antes:
```yaml
MONGODB_URL=mongodb://${MONGO_USERNAME:-admin}:${MONGO_PASSWORD:-password}@mongodb:27017
```

### Depois:
```yaml
MONGODB_URL=mongodb://${MONGO_USERNAME:-admin}:${MONGO_PASSWORD:-password}@mongodb:27017/?authSource=admin
```

## Arquivos Corrigidos
1. `docker-compose.yml` - Arquivo de produção
2. `docker-compose.dev.yml` - Arquivo de desenvolvimento
3. `start.sh` - Script de inicialização (melhorada a documentação das credenciais)

## Credenciais Padrão
As credenciais padrão para login no painel administrativo são:

- **Username**: `admin`
- **Password**: `admin_key_change_in_production`

**Nota**: Estas credenciais já estavam corretas no código e documentação. O problema era apenas a string de conexão do MongoDB.

## Como Testar a Correção

### 1. Limpar ambiente antigo
```bash
# Parar e remover containers e volumes existentes
docker compose down -v
```

### 2. Iniciar os containers
```bash
# Usando o script de inicialização
./start.sh

# OU manualmente
docker compose up --build -d
```

### 3. Verificar os logs
```bash
# Verificar se o MongoDB iniciou corretamente
docker compose logs mongodb

# Verificar se a API conectou ao MongoDB
docker compose logs fastapi

# Procurar pela mensagem "Conectado ao MongoDB: ticket_manager"
# e "Administrador inicial criado com sucesso"
```

### 4. Testar o login
1. Acesse http://localhost:8000/admin/login
2. Use as credenciais:
   - Username: `admin`
   - Password: `admin_key_change_in_production`
3. Você deve ser redirecionado para o dashboard

## Detalhes Técnicos

### Por que o `authSource=admin` é necessário?

Quando o MongoDB é inicializado com `MONGO_INITDB_ROOT_USERNAME` e `MONGO_INITDB_ROOT_PASSWORD`, ele cria o usuário no banco de dados `admin`. Portanto, ao se conectar, precisamos especificar que a autenticação deve ser feita contra o banco `admin`, mesmo que estejamos usando um banco de dados diferente (`ticket_manager`) para armazenar nossos dados.

### O que acontecia antes?

Sem o `authSource=admin`, o driver do MongoDB tentava autenticar contra o banco de dados especificado na conexão (neste caso, nenhum banco específico era especificado no path, então usava o padrão). Isso falhava porque o usuário `admin` não existe nesse banco - ele existe apenas no banco `admin`.

### Conformidade com .env.example

O arquivo `.env.example` já continha a string de conexão correta com `authSource=admin`:

```
MONGODB_URL=mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@mongodb:27017/?authSource=admin&authMechanism=SCRAM-SHA-256
```

Agora os arquivos `docker-compose.yml` e `docker-compose.dev.yml` estão alinhados com essa configuração.

**Nota sobre authMechanism**: O parâmetro `&authMechanism=SCRAM-SHA-256` é opcional nos arquivos docker-compose, pois o MongoDB 7.0 usa SCRAM-SHA-256 como mecanismo de autenticação padrão. Incluí-lo explicitamente no `.env.example` é uma boa prática para documentação, mas não é necessário para o funcionamento.

## Verificação de Segurança

Esta mudança é apenas de configuração e não afeta a segurança do sistema. Na verdade, ela garante que a autenticação funcione corretamente como previsto.

### Recomendações de Segurança para Produção:

1. **Altere as credenciais padrão** no arquivo `.env`:
   ```
   MONGO_USERNAME=seu_usuario_seguro
   MONGO_PASSWORD=sua_senha_forte_aqui
   ADMIN_USERNAME=seu_admin_username
   ADMIN_PASSWORD=sua_senha_admin_forte
   ```

2. **Configure JWT_SECRET_KEY** forte:
   ```bash
   openssl rand -hex 32
   ```

3. **Configure ENVIRONMENT=production** no `.env`

4. Use HTTPS em produção com certificados válidos

5. Configure CORS com domínios específicos (não use "*")
