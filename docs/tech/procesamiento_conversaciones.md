# Documentación: Procesamiento de Conversaciones en IANAE

## Arquitectura del Sistema

1. **chat_con_memoria.py** - Interfaz de usuario
2. **rag_server.py** - Motor RAG (procesa JSONs)
3. **ianae_memory_system.py** - Sistema de memoria

## Flujo de Procesamiento de JSONs

1. **Ubicación de archivos**: 
   `IANAE/memory/conversations_database/*.json`

2. **Componente principal**: 
   `buscar_conversaciones()` en `rag_server.py`

3. **Proceso detallado**:
   - Lista todos los archivos .json en el directorio
   - Excluye archivos que empiezan con '000_'
   - Para cada archivo:
     - Carga el JSON con `json.load()`
     - Extrae:
       - Título (campo 'title')
       - Mensajes (campo 'messages')
     - Calcula relevancia con keywords
     - Ordena por score de relevancia

4. **Estructura esperada del JSON**:
```json
{
  "title": "Título de la conversación",
  "created_at": "Fecha",
  "messages": [
    {
      "sender": "Remitente",
      "text": "Contenido del mensaje"
    }
  ]
}
```

## Métodos Clave

1. `buscar_conversaciones(pregunta)`
   - Busca en todos los JSONs
   - Devuelve las más relevantes

2. `construir_contexto_memoria(conversaciones)`
   - Formatea la información para IANAE
   - Incluye:
     - Títulos
     - Fechas  
     - Fragmentos de mensajes

3. `extract_keywords(texto)`
   - Procesa la pregunta del usuario
   - Extrae términos clave para la búsqueda

## Configuración

El archivo `config.json` controla:
- Ruta de los JSONs (`memory_path`)
- Número máximo de conversaciones a retornar
- Peso de keywords específicas

## Ejemplo de Uso

```python
rag = IANAEMemoryRAG()
conversaciones = rag.buscar_conversaciones("¿Recuerdas los proyectos de tacógrafos?")
contexto = rag.construir_contexto_memoria(conversaciones)
```

## Notas Importantes

- Los archivos deben ser JSON válidos
- Se espera una estructura específica de campos
- El sistema prioriza conversaciones recientes y con matches de keywords
- Los primeros 5 mensajes de cada conversación tienen más peso
