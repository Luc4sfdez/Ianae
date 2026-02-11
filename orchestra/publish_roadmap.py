#!/usr/bin/env python3
"""Publicar ROADMAP Fase A al docs-service"""

import requests
import json

# Leer roadmap
with open('E:/ianae-final/orchestra/ROADMAP_FASE_A.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Documento
doc = {
    "title": "ROADMAP Fase A: Desarrollo IANAE Autonomo - Plan Maestro Completo",
    "content": content,
    "category": "documentacion",
    "author": "arquitecto-daemon",
    "tags": ["fase-a", "roadmap", "worker-core", "worker-infra", "worker-nlp", "worker-ui"],
    "priority": "alta",
    "status": "completed"
}

# Publicar
try:
    r = requests.post('http://localhost:25500/api/v1/docs', json=doc)
    if r.status_code in [200, 201]:
        result = r.json()
        print(f"[OK] Roadmap publicado: #{result['id']}")
        print(f"     Titulo: {result['title'][:60]}...")
    else:
        print(f"[ERROR] Status {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"[ERROR] {e}")
