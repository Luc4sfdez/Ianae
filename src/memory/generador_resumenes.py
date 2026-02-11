#!/usr/bin/env python3
"""
generador_de_resumenes_v6.py

Script mejorado que:
1. Permite seleccionar carpetas o archivos específicos a procesar
2. Soporta tanto archivos JSON como MD (Markdown)
3. Mantiene la agrupación temática de la v5

Uso:
  python generador_de_resumenes_v6.py --input ruta/al/archivo.json --output carpeta_salida
  python generador_de_resumenes_v6.py --input ruta/al/archivo.md --output carpeta_salida
  python generador_de_resumenes_v6.py --input ruta/directorio --output carpeta_salida --filter "*.json,*.md"
"""

import json
import os
import sys
import re
import datetime
import argparse
from collections import Counter, defaultdict
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import glob

# Asegurarse de que los recursos necesarios estén disponibles
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# ----------------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------------

OUTPUT_DIR = "resumenes_tematicos_v6"
SIMILARITY_THRESHOLD = 0.3

# ----------------------------------------------------------------------------
# FUNCIONES DE EXTRACCIÓN DE CONVERSACIONES
# ----------------------------------------------------------------------------

def extract_from_markdown(md_file):
    """
    Extrae conversaciones de un archivo Markdown.
    """
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Dividir por marcadores de usuario y respuesta
        messages = []
        current_timestamp = datetime.datetime.fromtimestamp(
            os.path.getctime(md_file)
        ).isoformat()

        # Extraer bloques de conversación
        blocks = re.split(r'\n(?=\*\*User:\*\*|\bEdit\b)', content)
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            if block.startswith('**User:**'):
                # Es un mensaje del usuario
                text = block.replace('**User:**', '').strip()
                if text:
                    messages.append({
                        'uuid': f"msg_{len(messages)}",
                        'sender': 'human',
                        'text': text,
                        'timestamp': current_timestamp
                    })
            elif block.startswith('Edit'):
                # Es una respuesta del asistente
                text = block.replace('Edit', '').strip()
                if text:
                    messages.append({
                        'uuid': f"msg_{len(messages)}",
                        'sender': 'assistant',
                        'text': text,
                        'timestamp': current_timestamp
                    })

        if messages:
            return [{
                'metadata': {
                    'uuid': os.path.splitext(os.path.basename(md_file))[0],
                    'name': '',
                    'created_at': current_timestamp,
                    'updated_at': current_timestamp
                },
                'messages': messages,
                'full_text': ' '.join(msg['text'] for msg in messages)
            }]
        return []

    except Exception as e:
        print(f"Error al procesar archivo Markdown {md_file}: {e}")
        return []

def extract_from_json(json_file):
    """
    Extrae conversaciones de un archivo JSON.
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conversations = []
        
        if isinstance(data, list):
            for chat in data:
                if 'chat_messages' in chat:
                    messages = []
                    for msg in chat['chat_messages']:
                        if msg.get('content'):
                            message_text = ""
                            for content_item in msg['content']:
                                if content_item.get('text'):
                                    message_text += content_item['text'] + "\n"
                            
                            if message_text.strip():
                                messages.append({
                                    'uuid': msg.get('uuid', ''),
                                    'sender': msg.get('sender', ''),
                                    'text': message_text.strip(),
                                    'timestamp': msg.get('created_at', '')
                                })
                    
                    if messages:
                        conversations.append({
                            'metadata': {
                                'uuid': chat.get('uuid', ''),
                                'name': chat.get('name', ''),
                                'created_at': chat.get('created_at', ''),
                                'updated_at': chat.get('updated_at', '')
                            },
                            'messages': messages,
                            'full_text': ' '.join(msg['text'] for msg in messages)
                        })
        
        return conversations
    except Exception as e:
        print(f"Error al procesar archivo JSON {json_file}: {e}")
        return []

def extract_conversations_v6(file_path):
    """
    Extrae conversaciones según el tipo de archivo.
    """
    if file_path.lower().endswith('.json'):
        return extract_from_json(file_path)
    elif file_path.lower().endswith('.md'):
        return extract_from_markdown(file_path)
    else:
        print(f"Formato de archivo no soportado: {file_path}")
        return []

# ----------------------------------------------------------------------------
# FUNCIONES DE ANÁLISIS (se mantienen igual que en v5)
# ----------------------------------------------------------------------------

def extract_key_sentences(text, num_sentences=3):
    """Extrae las oraciones más relevantes del texto."""
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())
    
    stop_words = set(stopwords.words('spanish') + stopwords.words('english'))
    words = [word for word in words if word.isalnum() and word not in stop_words]
    
    freq_dist = FreqDist(words)
    
    sentence_scores = {}
    for sentence in sentences:
        score = 0
        for word in word_tokenize(sentence.lower()):
            if word in freq_dist:
                score += freq_dist[word]
        sentence_scores[sentence] = score
    
    important_sentences = sorted(sentence_scores.items(), 
                               key=lambda x: x[1], 
                               reverse=True)[:num_sentences]
    
    return [sentence for sentence, score in important_sentences]

def group_conversations_by_topic(conversations):
    """Agrupa conversaciones relacionadas basándose en similitud."""
    if not conversations:
        return []
    
    texts = [conv['full_text'] for conv in conversations]
    
    vectorizer = TfidfVectorizer(
        stop_words=stopwords.words('spanish') + stopwords.words('english'),
        max_features=1000
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    similarity_matrix = cosine_similarity(tfidf_matrix)
    
    groups = []
    used = set()
    
    for i in range(len(conversations)):
        if i in used:
            continue
            
        group = {
            'main_conversation': conversations[i],
            'related_conversations': [],
            'keywords': set(),
            'common_topics': []
        }
        
        for j in range(len(conversations)):
            if i != j and j not in used and similarity_matrix[i][j] > SIMILARITY_THRESHOLD:
                group['related_conversations'].append(conversations[j])
                used.add(j)
        
        used.add(i)
        
        all_texts = [group['main_conversation']['full_text']] + \
                   [conv['full_text'] for conv in group['related_conversations']]
        
        words = []
        for text in all_texts:
            words.extend(word_tokenize(text.lower()))
        
        stop_words = set(stopwords.words('spanish') + stopwords.words('english'))
        words = [word for word in words if word.isalnum() and word not in stop_words]
        
        freq_dist = FreqDist(words)
        group['keywords'] = set(word for word, _ in freq_dist.most_common(10))
        
        topics = extract_key_sentences(' '.join(all_texts))
        group['common_topics'] = topics
        
        groups.append(group)
    
    return groups

def identify_technical_details_v6(messages):
    """Identifica detalles técnicos relevantes."""
    tech_details = {
        'commands': set(),
        'configurations': set(),
        'file_paths': set(),
        'urls': set(),
        'error_messages': set()
    }
    
    for msg in messages:
        text = msg['text']
        
        commands = re.findall(r'`([^`]+)`|(?<=\$ )(.*?)(?=\n|$)', text)
        tech_details['commands'].update([cmd[0] or cmd[1] for cmd in commands if any(cmd)])
        
        configs = re.findall(r'(\w+)=(["\'][^"\']+["\']|\S+)', text)
        tech_details['configurations'].update([f"{k}={v}" for k, v in configs])
        
        paths = re.findall(r'(?:\/[\w\-. ]+)+', text)
        tech_details['file_paths'].update(paths)
        
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        tech_details['urls'].update(urls)
        
        errors = re.findall(r'(?:error|exception|failed):[^\n]+', text, re.IGNORECASE)
        tech_details['error_messages'].update(errors)
    
    return {k: list(v) for k, v in tech_details.items() if v}

def identify_problems_solutions_v6(messages):
    """Identifica problemas y sus soluciones."""
    issues = []
    current_issue = None
    
    for msg in messages:
        text = msg['text'].lower()
        
        if msg['sender'] == 'human' and any(word in text for word in ['error', 'problema', 'fallo', 'no funciona', 'ayuda']):
            if current_issue:
                issues.append(current_issue)
            current_issue = {
                'problem': extract_key_sentences(msg['text'], 1)[0],
                'timestamp': msg['timestamp'],
                'solutions': []
            }
        
        elif current_issue and msg['sender'] == 'assistant':
            solution_indicators = ['solución', 'debes', 'puedes', 'hay que', 'necesitas']
            if any(indicator in text for indicator in solution_indicators):
                current_issue['solutions'].append({
                    'text': extract_key_sentences(msg['text'], 1)[0],
                    'timestamp': msg['timestamp']
                })
    
    if current_issue:
        issues.append(current_issue)
    
    return issues

def extract_code_blocks_v6(messages):
    """Extrae y clasifica bloques de código."""
    code_blocks = []
    
    for msg in messages:
        if msg['sender'] == 'assistant':
            blocks = re.findall(r'```(\w*)\n([\s\S]+?)\n```', msg['text'])
            
            for lang, code in blocks:
                if code.strip():
                    if not lang:
                        if re.search(r'\b(?:def|class|import|print)\b', code):
                            lang = "python"
                        elif re.search(r'\b(?:function|const|let|var)\b', code):
                            lang = "javascript"
                        elif re.search(r'\b(?:sudo|apt|yum|dnf)\b', code):
                            lang = "bash"
                        else:
                            lang = "code"
                    
                    description = ""
                    if lang in ["python", "javascript"]:
                        comments = re.findall(r'#.*$|//.*$', code, re.MULTILINE)
                        description = ' '.join(comments)
                    
                    code_blocks.append({
                        'language': lang,
                        'code': code.strip(),
                        'description': description,
                        'context': extract_key_sentences(msg['text'], 1)[0],
                        'timestamp': msg['timestamp']
                    })
    
    return code_blocks

def create_topic_summary_v6(group):
    """Genera resumen estructurado para un grupo temático."""
    main_conv = group['main_conversation']
    related_convs = group['related_conversations']
    
    title = main_conv['metadata']['name']
    if not title:
        title = group['common_topics'][0] if group['common_topics'] else "Tema sin título"
    
    all_messages = main_conv['messages'] + \
                  [msg for conv in related_convs for msg in conv['messages']]
    
    all_messages.sort(key=lambda x: x['timestamp'])
    
    markdown = f"""# {title.upper()}

## Resumen del Tema
"""
    
    markdown += "\n### Puntos Principales\n"
    for topic in group['common_topics']:
        markdown += f"- {topic}\n"
    
    markdown += f"\n**Palabras clave:** {', '.join(group['keywords'])}\n"
    
    markdown += "\n## Conversaciones Relacionadas\n"
    
    markdown += f"\n### Conversación Principal\n"
    markdown += f"- **ID:** {main_conv['metadata']['uuid']}\n"
    markdown += f"- **Fecha:** {main_conv['metadata']['created_at']}\n"
    
    if related_convs:
        markdown += "\n### Conversaciones Relacionadas\n"
        for conv in related_convs:
            markdown += f"- **ID:** {conv['metadata']['uuid']}\n"
            markdown += f"  **Fecha:** {conv['metadata']['created_at']}\n"
    
    issues = identify_problems_solutions_v6(all_messages)
    if issues:
        markdown += "\n## Problemas y Soluciones\n"
        for issue in issues:
            markdown += f"\n### Problema ({issue['timestamp']})\n{issue['problem']}\n"
            if issue['solutions']:
                markdown += "\n**Soluciones:**\n"
                for solution in issue['solutions']:
                    markdown += f"- {solution['text']}\n"
    
    tech_details = identify_technical_details_v6(all_messages)
    if tech_details:
        markdown += "\n## Detalles Técnicos\n"
        for category, details in tech_details.items():
            if details:
                markdown += f"\n### {category.replace('_', ' ').title()}\n"
                for detail in details[:5]:
                    markdown += f"- `{detail}`\n"
    
    code_blocks = extract_code_blocks_v6(all_messages)
    if code_blocks:
        markdown += "\n## Ejemplos de Código\n"
        for block in code_blocks:
            markdown += f"\n### {block['language'].title()} - {block['timestamp']}\n"
            if block['description']:
                markdown += f"**Descripción:** {block['description']}\n"
            if block['context']:
                markdown += f"**Contexto:** {block['context']}\n"
            markdown += f"```{block['language']}\n{block['code']}\n```\n"
    
    return markdown

def create_topic_index_v6(groups, output_dir):
    """Crea página índice de temas."""
    index_content = """# ÍNDICE DE TEMAS

A continuación se listan todos los temas identificados, ordenados por fecha de la conversación más reciente:

"""
    
    sorted_groups = sorted(
        groups,
        key=lambda x: max(
            x['main_conversation']['metadata']['created_at'],
            *(conv['metadata']['created_at'] for conv in x['related_conversations'])
        ),
        reverse=True
    )
    
    for i, group in enumerate(sorted_groups, 1):
        main_conv = group['main_conversation']
        title = main_conv['metadata']['name'] or group['common_topics'][0]
        
        index_content += f"## {i}. [{title}](./tema_{i}.md)\n"
        index_content += f"**Palabras clave:** {', '.join(group['keywords'])}\n\n"
        
        index_content += "**Conversaciones incluidas:**\n"
        index_content += f"- Principal: {main_conv['metadata']['created_at']} (ID: {main_conv['metadata']['uuid']})\n"
        
        for conv in group['related_conversations']:
            index_content += f"- Relacionada: {conv['metadata']['created_at']} (ID: {conv['metadata']['uuid']})\n"
        
        index_content += "\n"
    
    index_path = os.path.join(output_dir, "index.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    return index_path

def process_files_v6(input_paths, output_dir):
    """
    Procesa los archivos especificados y genera resúmenes temáticos.
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        all_conversations = []
        
        # Procesar cada archivo
        for input_path in input_paths:
            if os.path.isfile(input_path):
                conversations = extract_conversations_v6(input_path)
                all_conversations.extend(conversations)
            elif os.path.isdir(input_path):
                for root, _, files in os.walk(input_path):
                    for file in files:
                        if file.endswith(('.json', '.md')):
                            file_path = os.path.join(root, file)
                            conversations = extract_conversations_v6(file_path)
                            all_conversations.extend(conversations)
        
        if not all_conversations:
            print("⚠️ No se encontraron conversaciones para procesar")
            return False
        
        # Agrupar por tema
        groups = group_conversations_by_topic(all_conversations)
        
        # Procesar cada grupo
        for i, group in enumerate(groups, 1):
            output_file = os.path.join(output_dir, f"tema_{i}.md")
            summary = create_topic_summary_v6(group)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"✅ Resumen del tema {i} guardado en: {output_file}")
        
        # Crear índice
        index_path = create_topic_index_v6(groups, output_dir)
        print(f"📑 Índice de temas generado en: {index_path}")
        
        return True
        
    except Exception as e:
        print(f"Error procesando archivos: {e}")
        return False

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description='Genera resúmenes temáticos de conversaciones en archivos JSON y MD.'
    )
    parser.add_argument(
        '--input',
        nargs='+',
        required=True,
        help='Archivos o directorios a procesar'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Directorio para guardar resúmenes',
        default=OUTPUT_DIR
    )
    parser.add_argument(
        '--filter',
        help='Patrón para filtrar archivos (ejemplo: "*.json,*.md")',
        default="*.json,*.md"
    )
    
    args = parser.parse_args()
    
    try:
        # Expandir patrones de filtro
        input_paths = []
        for path in args.input:
            if os.path.isfile(path):
                input_paths.append(path)
            elif os.path.isdir(path):
                for pattern in args.filter.split(','):
                    pattern = pattern.strip()
                    glob_pattern = os.path.join(path, '**', pattern)
                    input_paths.extend(glob.glob(glob_pattern, recursive=True))
        
        if not input_paths:
            print(f"Error: No se encontraron archivos que coincidan con los criterios")
            return 1
        
        print(f"Procesando {len(input_paths)} archivos...")
        if process_files_v6(input_paths, args.output):
            print("\n🎉 Procesamiento completado con éxito")
            return 0
        else:
            print("\n⚠️ El procesamiento falló")
            return 1
        
    except Exception as e:
        print(f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
