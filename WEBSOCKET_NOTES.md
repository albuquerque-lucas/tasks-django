WebSocket notifications e presence

Rota WebSocket
- URL: ws://<host>/ws/notifications/
- Conexao unica (notifications + presence na mesma conexao)

Autenticacao (JWTAuthMiddlewareStack)
- Token via query string: ?token=<jwt>
- Exemplo: ws://localhost:8000/ws/notifications/?token=SEU_JWT
- Se o token for invalido/expirado, a conexao sera recusada (code 4401)

Modelo de conexao
- Cada usuario autenticado entra no grupo: user_<id>
- Eventos do servidor sao enviados para grupos por usuario

Contrato de eventos (estavel com o frontend)
- Os nomes dos eventos abaixo sao o contrato estavel com o frontend.
- Alteracoes nesses nomes exigem ajuste do cliente.

Eventos de notifications (existentes)
- notification.created
- Payload:
  - event: "notification.created"
  - notification_id: <int>
- Exemplo (servidor -> cliente):
  {
    "event": "notification.created",
    "notification_id": 123
  }

Presence (novo)

Eventos emitidos pelo servidor
- user_online
- user_offline

Payload padrao (servidor -> cliente)
- event: "user_online" | "user_offline"
- user_id: <int>
- is_online: <bool>
- last_seen_at: <string ISO 8601> | null

Formato de last_seen_at
- ISO 8601, sempre com timezone (offset, ex.: -03:00)
- Pode ser null quando o usuario nunca teve presenca registrada

Exemplo (servidor -> cliente):
{
  "event": "user_online",
  "user_id": 42,
  "is_online": true,
  "last_seen_at": "2026-02-02T14:45:10-03:00"
}

Eventos recebidos do cliente
- presence.heartbeat
- presence.ping

Exemplo (cliente -> servidor):
{
  "event": "presence.heartbeat"
}

Heartbeat esperado
- Intervalo recomendado: a cada 30s
- Ausencia de heartbeat (ou desconexao) faz o status expirar via TTL no cache
- O servidor renova o TTL quando recebe heartbeat

Regras de visibilidade
- super_admin e company_admin veem todos
- demais usuarios veem apenas usuarios de equipes em comum (ou a si mesmos)

Snapshot REST (obrigatorio para estado inicial)

Endpoints
- GET /users/presence/
- GET /users/presence/?team=<id>

Query params suportados
- team=<id>

Campos retornados
- id
- username
- first_name
- last_name
- last_seen_at
- is_online

Exemplo de resposta (GET /users/presence/)
[
  {
    "id": 1,
    "username": "ana.silva",
    "first_name": "Ana",
    "last_name": "Silva",
    "last_seen_at": "2026-02-02T14:45:10-03:00",
    "is_online": true
  },
  {
    "id": 2,
    "username": "carlos.souza",
    "first_name": "Carlos",
    "last_name": "Souza",
    "last_seen_at": null,
    "is_online": false
  }
]

Uso recomendado no frontend
- Sempre carregar o snapshot inicial via REST
- Usar o WebSocket apenas para atualizacoes em tempo real (user_online/user_offline)

Integracao esperada no frontend React (repo separado)
- Conectar no WebSocket apos login (usar o JWT do usuario)
- Enviar heartbeat periodico (presence.heartbeat) a cada 30s
- Atualizar a lista de usuarios ao receber user_online/user_offline
- Regra de renderizacao:
  - se is_online = true => exibir online
  - se is_online = false => exibir offline + fallback visual com last_seen_at

Multiplas abas/dispositivos (comportamento atual)
- Nao existe contagem de conexoes por usuario.
- Se uma aba desconectar, o servidor pode emitir user_offline mesmo com outra aba conectada.
- O TTL/heartbeat tende a corrigir o status assim que a outra aba enviar heartbeat.

Troubleshooting rapido
- 4401: token invalido ou expirado.
- WS conecta mas nao recebe eventos: validar URL e token do usuario.
- Presenca nao atualiza: validar heartbeat do cliente e TTL configurado no servidor.

Restricoes
- Nao criar novos WebSockets
- Nao persistir is_online no banco
