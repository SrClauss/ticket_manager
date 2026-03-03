# ✅ Checklist de Implementação - Editor de Layout de Ingressos

**Versão do checklist:** 1.0  
**Baseado em:** docs/PLANO_IMPLEMENTACAO_EDITOR_LAYOUT.md

---

## Instruções
- Marque cada item quando estiver concluído.
- Use a seção "Notas" para observações e bloqueios.

---

## Pré-requisitos
- [ ] Aprovação do plano por stakeholder
- [ ] Criar branch `feature/new-layout-editor`

---

## FASE 1: Setup Base (2-3 horas)
- [ ] Adicionar Alpine.js via CDN
- [ ] Criar estrutura HTML base (sidebar + canvas + preview)
- [ ] Implementar Alpine.store com estado inicial (canvas, elements, selected)
- [ ] Configurar Interact.js para drag básico
- [ ] Criar CSS base para layout grid (layout-editor, sidebar, canvas, preview)
- [ ] Commit inicial e abrir PR

---

## FASE 2: Canvas & Elementos (4-5 horas)
- [ ] Renderizar elementos no canvas via Alpine (text, qrcode, logo, divider)
- [ ] Habilitar drag & drop com atualização de posição visual
- [ ] Implementar botão "Confirmar Posição" que converte px→mm e atualiza estado
- [ ] Implementar conversão px ↔ mm consistente e testada
- [ ] Adicionar réguas horizontais e verticais
- [ ] Seleção de elementos (click) e destaque visual
- [ ] Commit e revisão

---

## FASE 3: Sidebar - Adicionar Elementos (3-4 horas)
- [ ] Formulário dinâmico por tipo de elemento (text/qrcode/logo/divider)
- [ ] Botões de tags inteligentes que inserem {NOME}, {CPF}, etc.
- [ ] Adicionar funcionalidade de upload ou seleção de logo do evento (simples)
- [ ] Lista de elementos (reordenar por drag, delete com confirmação)
- [ ] Commit e revisão

---

## FASE 4: Painel de Propriedades (3-4 horas)
- [ ] Painel de propriedades exibido ao selecionar elemento
- [ ] Inputs X/Y em mm sincronizados com drag
- [ ] Propriedades específicas por tipo (size_mm para qrcode/logo, font/size para texto)
- [ ] Formatação de texto (bold, italic, underline, strikethrough)
- [ ] Alinhamento rápido (left/center/right) com validação de overflow
- [ ] Commit e revisão

---

## FASE 5: Preview em Tempo Real (2-3 horas)
- [ ] Endpoint `/admin/eventos/layout/{evento_id}/preview` (POST) aceita estado atual
- [ ] Implementar debounce (500ms) para auto-refresh
- [ ] Mostrar dados fictícios: `Edson Arantes do Nascimento` / `CPF: 123.456.789-00`
- [ ] Implementar loading state e tratamento de erro
- [ ] Commit e revisão

---

## FASE 6: Templates & Histórico (3-4 horas)
- [ ] Criar templates padrão (`padrao_vip`, `simples`) no backend
- [ ] Endpoint para listar/carregar templates
- [ ] Aplicar template automaticamente ao criar evento
- [ ] Implementar undo/redo (limite 50 estados) e atalhos Ctrl+Z/Ctrl+Shift+Z
- [ ] Commit e revisão

---

## FASE 7: Validações & Salvamento (2-3 horas)
- [ ] Implementar validações client-side (fora do canvas, overflow right-align, QR size)
- [ ] Implementar mensagens (toasts) para erros/avisos
- [ ] Implementar endpoint de salvamento `/admin/eventos/{evento_id}/layout/save`
- [ ] Testes de integração (salvar / recuperar layout)
- [ ] Commit e revisão

---

## FASE 8: Responsividade & Polish (3-4 horas)
- [ ] Media queries para desktop/tablet/mobile
- [ ] Touch-friendly drag no mobile (teste manual)
- [ ] Fixed save bar no mobile
- [ ] Micro-interações e acessibilidade básica
- [ ] Commit e revisão

---

## FASE 9: Testes & Deploy (2-3 horas)
- [ ] Testar fluxo completo (adicionar, editar, posicionar, salvar)
- [ ] Testar undo/redo e histórico
- [ ] Testar preview com dados reais e com layouts complexos
- [ ] Documentar uso do editor no README e /docs
- [ ] Deploy em staging e smoke tests
- [ ] Deploy em produção

---

## Checklist de Aceitação (QA)
- [ ] Drag & drop fluido em desktop
- [ ] Inputs X/Y sincronizam com drag (confirmação de posição disponível)
- [ ] Preview atualiza automaticamente (debounce OK)
- [ ] Templates carregam e se aplicam corretamente
- [ ] Undo/Redo funcional
- [ ] Salvar persiste no MongoDB e recarrega corretamente
- [ ] Validations bloqueiam saves inválidos
- [ ] Réguas aparecem com medidas em mm
- [ ] QR Codes renderizam corretamente
- [ ] Lista de elementos reordenável e funcional

---

## Notas / Bloqueios
- [ ] Observação: manter tudo em vanilla + Alpine.js; evitar migrar para React neste momento
- [ ] Bloqueio: definir se será necessário suporte a múltiplas logos (por enquanto 1)

---

## Próximos Passos Imediatos
- [ ] Confirmar aprovação do checklist
- [ ] Criar branch `feature/new-layout-editor` e iniciar FASE 1

---

*Arquivo gerado automaticamente a partir de PLANO_IMPLEMENTACAO_EDITOR_LAYOUT.md*