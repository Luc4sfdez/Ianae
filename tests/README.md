# Tests IANAE

Suite de tests completa para IANAE.

## Estructura

```
tests/
├── unit/              Tests unitarios por módulo
│   ├── test_nucleo.py
│   ├── test_emergente.py
│   └── test_conceptos.py
├── integration/       Tests de integración
│   └── test_full_system.py
├── benchmarks/        Benchmarks de rendimiento
│   └── benchmark_nucleo.py
└── fixtures/          Datos de prueba
    └── sample_networks.json
```

## Ejecutar Tests

```bash
# Todos los tests
pytest tests/

# Solo unitarios
pytest tests/unit/

# Solo benchmarks
pytest tests/benchmarks/ -v

# Con cobertura
pytest tests/ --cov=src/core --cov-report=html
```

## Requisitos

```bash
pip install pytest pytest-cov
```

## Convenciones

- Nombres: `test_<modulo>_<funcionalidad>.py`
- Un test por función/método
- Usar fixtures para datos comunes
- Documentar casos edge
