# API Documentation

Generated: 2026-01-25T10:35:33.827Z

NOTE: All lead-related endpoints and public lead pages have been removed per request.

This document lists the API endpoints available in the application and how to use them.

General notes
- Many routers are mounted in the application; paths below are the route paths defined within each router file. Depending on the FastAPI application mount points, a prefix (e.g. `/portaria`, `/bilheteria`, `/admin`, etc.) may be applied. Check the application startup code to confirm the exact full path.
- Authentication: endpoints that depend on a token use dependencies like `verify_token_portaria`, `verify_token_bilheteria`, or `verify_admin_access`. Include the appropriate Authorization header or token as required by each module.

Portaria (app/routers/portaria.py)
- GET /evento
  - Response model: EventoInfoPortaria
  - Auth: Depends on verify_token_portaria (token required)
  - Description: Returns basic event info for portaria (gate) module. Callers should supply the portaria token to identify the event.

- GET /ingresso/{qrcode_hash}
  - Response model: IngressoDetalhes
  - Auth: Depends on verify_token_portaria
  - Description: Fetch full details for a ticket by its QR code hash, including participant name/email/phone, ticket type, event name, status, emission date and permissions.
  - Example: GET /ingresso/abcd1234 (with portaria token)

- POST /validar
  - Request: ValidacaoRequest (qrcode_hash, ilha_id)
  - Response: ValidacaoResponse
  - Auth: Depends on verify_token_portaria
  - Description: Validate that a ticket is allowed to access a specific "ilha" (sector). Records the validation in validacoes_acesso and returns OK or NEGADO with message.

- GET /ilhas
  - Response: list of ilhas (sectors) for the event
  - Auth: Depends on verify_token_portaria
  - Description: Returns island/sector information for the event (either embedded in the event document or from ilhas collection).

- GET /estatisticas
  - Auth: Depends on verify_token_portaria
  - Description: Returns validation statistics (total validations, per-island counts, latest validations).

Bilheteria (app/routers/bilheteria.py)
- GET /evento
  - Response model: EventoInfo
  - Auth: Depends on verify_token_bilheteria
  - Description: Returns event info and available ticket types.

- POST /participantes
  - Request: ParticipanteCreate
  - Response model: Participante
  - Auth: Depends on verify_token_bilheteria
  - Description: Create a participant (quick add). If email exists, returns existing participant.

- POST /emitir
  - Request: EmissaoIngressoRequest (tipo_ingresso_id, participante_id)
  - Response: EmissaoIngressoResponse (ingresso, layout_preenchido)
  - Auth: Depends on verify_token_bilheteria
  - Description: Issues a ticket for a participant, generates a qrcode_hash and returns a filled layout for printing.

- GET /participante/{participante_id}
  - Response model: Participante
  - Auth: Depends on verify_token_bilheteria
  - Description: Retrieve participant by ID.

- GET /participantes/list?page=1&per_page=20&nome=
  - Response model: ParticipantesListResponse
  - Auth: Depends on verify_token_bilheteria
  - Description: Returns a paginated list of participants for the event. Supports filtering by name (case insensitive regex).
  - Query parameters:
    - page: Page number (default: 1, minimum: 1)
    - per_page: Items per page (default: 20, minimum: 1, maximum: 100)
    - nome: Optional name filter (case insensitive regex)
  - Response fields:
    - participantes: List of Participante objects
    - total_count: Total number of participants (filtered or not)
    - total_pages: Total number of pages based on per_page
    - current_page: Current page number
    - per_page: Items per page

- GET /participantes/buscar?nome=&email=&cpf=
  - Response: List[Participante]
  - Auth: Depends on verify_token_bilheteria
  - Description: Search participants by name/email/CPF.

- GET /busca-credenciamento?nome=&email=
  - Response: List[Dict]
  - Auth: Depends on verify_token_bilheteria
  - Description: Optimized search for credential re-printing.

- POST /reimprimir/{ingresso_id}
  - Response: EmissaoIngressoResponse
  - Auth: Depends on verify_token_bilheteria
  - Description: Re-print an existing ticket (by ingresso_id), returns ingresso data and prefilled layout.

Admin API and Web (app/routers/admin.py, app/routers/admin_web.py)
- Many admin routes require `verify_admin_access` dependency. The admin web routes serve HTML templates (response_class=HTMLResponse) for admin UI pages like /login, /dashboard, /eventos, etc.
- Admin API routes provide CRUD operations for events, ilhas and tipos_ingresso. Consult the source files for precise request/response models and required fields.

Event API (app/routers/evento_api.py)
- GET /labels/generate.png
  - Description: Generates labels for printing (image response).

- GET /{evento_id}/ingresso/{ingresso_id}/render.jpg
  - Description: Renders an ingresso image for a given event and ingresso id.

- GET /{evento_id}/ingresso/{ingresso_id}/meta
  - Description: Returns metadata for an ingresso used for rendering.

Planilha (app/routers/planilha.py)
- GET /upload/{token}
  - Response: HTML form for uploading spreadsheets.

- GET /upload/{token}/template.xlsx
  - Response: Downloadable XLSX template.

- GET /eventos/{evento_id}/planilha-importacao/{import_id}
  - Response: Status/details of an import job.

Operational Web (app/routers/operational_web.py)
- NOTE: Lead collector and auto-credenciamento endpoints/pages have been removed.
- Remaining operational pages serve HTML templates under app/templates/operational/.

Security notes and recommendations
- Many endpoints expose participant PII. Ensure that the proper token validation dependencies are used and that tokens are issued and rotated securely.
- Consider rate-limiting endpoints that accept qrcode_hash to avoid enumeration attacks.
- For any public interfaces (e.g., rendering images), ensure they do not leak sensitive participant data.

If desired I can:
- Generate an OpenAPI spec file (JSON/YAML) for all active endpoints.
- Reintroduce a protected lead-collector route that requires a specific token and logs interactions.

-- End of document
