## Task Processor

Aplicação simples de processamento de lista de tarefas, usado para por em pratica leituras sobre Arquitetura em Serviços.

## Subindo os serviços com banco compartilhado

Os serviços `task` e `user` usam a mesma variável `DATABASE_URL` e apontam para o mesmo PostgreSQL no `docker-compose`.

1. Suba todos os containers:

```bash
docker compose up --build
```

2. Teste os endpoints de saúde:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

Se a conexão estiver correta, ambos retornam `"database": "connected"`.

## Migracoes e tabelas iniciais

As migracoes ficam em `infra/migrations` e sao executadas por um servico dedicado no Docker Compose.

1. Suba o banco:

```bash
docker compose up -d postgres
```

2. Execute as migracoes:

```bash
docker compose --profile tools run --rm migrations
```

3. (Opcional) Verifique as tabelas criadas:

```bash
docker compose exec -T postgres psql -U task_user -d task_db -c "\\dt"
```