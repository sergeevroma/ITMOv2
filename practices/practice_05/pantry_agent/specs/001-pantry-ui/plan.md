# Implementation Plan: pantry-ui

**Branch**: `001-pantry-ui` | **Date**: 2026-10-22 | **Spec**: specs/001-pantry-ui/spec.md

**Input**: Feature specification from `specs/001-pantry-ui/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.10 (per project)

**Primary Dependencies**: Flask, Jinja2, pytest

**Storage**: N/A

**Testing**: pytest (Flask test client for UI), команда: `PYTHONPATH=src .venv/bin/python -m pytest -q`

**Target Platform**: Linux server (current environment)

**Project Type**: Web service with server-rendered UI

**Performance Goals**: UI round-trip perceived < 1s for 95% валидных запросов (см. SC-001)

**Constraints**: Соблюдать контракт V1, единое ядро планирования/валидации, детерминизм сортировки/limit/score

**Scale/Scope**: Минимальный UI (одна страница форма+результаты)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates determined based on constitution file:
- MUST: Единое ядро планирования/валидации для API и UI (UI не вычисляет score/сортировку/limit)
- MUST: Стабильность контракта API V1
- MUST: Детерминированная нормализация и порядок; `limit` применяется последним
- MUST: Тесты покрывают планирование/валидацию/сортировку/score; Flask test client для UI

## Project Structure

### Documentation (this feature)

```text
specs/001-pantry-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── ui-form-contract.md
│   ├── api-contract.md
│   └── parity-tests.md
└── tasks.md (создаётся /speckit.tasks)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: Документация фичи хранится в `specs/001-pantry-ui/`. Шаблоны UI в `src/templates/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
