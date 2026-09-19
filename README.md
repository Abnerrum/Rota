# RotaIA — Plataforma Inteligente de Operações de Campo

Plataforma brasileira para gestão de ordens de serviço, equipes externas, planejamento de rotas, SLA e integração de telemetria.

## O que já existe

- Dashboard operacional responsivo
- Ordens de serviço com prioridade e risco de SLA
- Equipes com capacidade e especialidades
- Mapa com OpenStreetMap + Leaflet
- Otimização de distribuição de OS
- Estratégia por técnico mais próximo
- Estratégia balanceada por distância + carga + disponibilidade
- Filtro de OS por prioridade e situação de SLA
- Endpoint de saúde da API
- Integração opcional com Cobli
- FastAPI + Docker
- Interface web sem dependência de framework frontend

## Otimizador v0.3

A distribuição agora considera:

1. prioridade da OS;
2. tempo restante de SLA;
3. compatibilidade da especialidade do técnico;
4. distância estimada;
5. capacidade de atendimento do técnico;
6. carga já atribuída;
7. disponibilidade atual da equipe.

Estratégias disponíveis:

- `balanced`: busca equilíbrio entre distância e carga;
- `nearest`: seleciona o técnico compatível mais próximo.

### Exemplo

```http
POST /api/optimize?strategy=balanced
```

A resposta inclui distância estimada, carga atribuída e resumo do planejamento.

## Endpoints principais

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/orders`
- `GET /api/orders?priority=Crítica`
- `GET /api/orders?risk=Atenção`
- `GET /api/technicians`
- `POST /api/optimize?strategy=balanced`
- `POST /api/optimize?strategy=nearest`

## Integração Cobli

A chave fica exclusivamente no backend. **Nunca publique sua chave no GitHub.**

1. Gere ou obtenha uma chave de API no painel Cobli.
2. Copie `.env.example` para `.env`.
3. Preencha `COBLI_API_KEY`.
4. Execute:

```bash
docker compose up --build
```

Acesse:

- Aplicação: http://localhost:8000
- Swagger: http://localhost:8000/docs

### Endpoints Cobli

- `GET /api/cobli/status`
- `GET /api/cobli/drivers`
- `GET /api/cobli/devices`
- `GET /api/cobli/routes`
- `GET /api/cobli/paths?startDate=...&endDate=...`

## Arquitetura planejada

```text
Frontend Web / PWA
        |
     FastAPI
        |
  Serviço de Rotas
   /      |      \
Postgres  Redis   Integrações
PostGIS           Cobli / Maps
        |
 Motor de otimização
 OR-Tools / OSRM
        |
 IA Operacional
```

## Próximas evoluções

- PostgreSQL + PostGIS
- Autenticação JWT e multiempresa
- Cadastro real de clientes, técnicos, veículos e OS
- OR-Tools para Vehicle Routing Problem
- OSRM para distância e tempo por malha viária
- Rastreamento GPS em tempo real
- App/PWA do técnico
- Check-in e check-out por geolocalização
- Evidências de atendimento com foto e assinatura
- Estoque de peças e materiais
- Histórico completo da OS
- Notificações por WhatsApp/e-mail/push
- BI com TAT, SLA, produtividade e custo/km
- Previsão de atraso com IA
- Replanejamento automático por trânsito, ausência ou emergência
- Auditoria e controle de acesso por perfil
- Testes automatizados e CI/CD

## Visão do produto

A ideia do RotaIA é evoluir de um planejador de rotas para uma plataforma operacional completa para empresas que possuem equipes em campo, como:

- assistência técnica;
- telecom;
- energia;
- logística;
- manutenção;
- facilities;
- instalação;
- delivery B2B;
- serviços externos.

O objetivo é centralizar **ordens, equipes, rotas, SLA, frota, telemetria e inteligência operacional** em uma única plataforma.

---

Projeto desenvolvido por **Abner Luiz Pascoal de Oliveira**.
