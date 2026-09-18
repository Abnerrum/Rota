# Rota — Plataforma Inteligente de Operações de Campo

MVP para gestão de ordens de serviço, equipes, planejamento de rotas e integração de telemetria.

## Recursos
- Dashboard operacional
- Ordens de serviço e equipes
- OpenStreetMap/Leaflet
- Distribuição inicial de OS por proximidade
- Integração opcional com API Cobli: motoristas, dispositivos, rotas e trajetos
- FastAPI + Docker

## Configuração da Cobli
A integração usa a chave no backend. **Nunca publique sua chave no GitHub.**

1. No painel Cobli, gere/obtenha uma chave de API.
2. Copie `.env.example` para `.env`.
3. Preencha `COBLI_API_KEY`.
4. Execute:
```bash
docker compose up --build
```

Acesse http://localhost:8000 e a documentação da API em http://localhost:8000/docs.

## Endpoints Cobli do Rota
- `GET /api/cobli/status`
- `GET /api/cobli/drivers`
- `GET /api/cobli/devices`
- `GET /api/cobli/routes`
- `GET /api/cobli/paths?startDate=...&endDate=...`

## Roadmap
PostgreSQL/PostGIS, autenticação multiempresa, OR-Tools/OSRM, app do técnico, frota, estoque, BI, notificações e IA operacional.
