#!/usr/bin/env python3
"""
auto_detector.py - Detector automático de formatos de conversaciones (CORREGIDO)
Detecta y procesa ChatGPT, Claude, Cline/Continue automáticamente
"""

import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path

class AutoDetector:
    """Detector inteligente de formatos de conversaciones"""
    
    def __init__(self):
        self.conversation_patterns = {
            'chatgpt': {
                'json_keys': ['mapping', 'conversation_id', 'create_time'],
                'structure_indicators': ['mapping', 'message', 'author', 'role'],
                'confidence_threshold': 0.7
            },
            'claude': {
                'json_keys': ['conversation_id', 'name', 'chat_messages'],
                'structure_indicators': ['chat_messages', 'sender', 'text', 'uuid'],
                'confidence_threshold': 0.8
            },
            'cline': {
                'text_patterns': [
                    r'# Cline Task',
                    r'## Human:',
                    r'## Assistant:',
                    r'### Human',
                    r'### Assistant',
                    r'**Human:**',
                    r'**Assistant:**'
                ],
                'confidence_threshold': 0.6
            }
        }
    
    def detect_format(self, file_path: str) -> Tuple[str, float, Dict]:
        """
        Detecta el formato del archivo de conversación
        
        Returns:
            (formato, confianza, metadatos)
        """
        try:
            # Leer contenido del archivo
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Intentar detectar como JSON primero
            json_result = self._detect_json_format(content)
            if json_result[1] > 0.5:  # Si confianza > 0.5
                return json_result
            
            # Si no es JSON válido, probar como texto/markdown
            text_result = self._detect_text_format(content)
            return text_result
            
        except Exception as e:
            return 'unknown', 0.0, {'error': str(e)}
    
    def _detect_json_format(self, content: str) -> Tuple[str, float, Dict]:
        """Detecta formatos JSON (ChatGPT, Claude)"""
        try:
            data = json.loads(content)
            
            # Detectar ChatGPT
            chatgpt_score = self._score_chatgpt(data)
            if chatgpt_score > self.conversation_patterns['chatgpt']['confidence_threshold']:
                return 'chatgpt', chatgpt_score, {'structure': 'json', 'conversations_detected': self._count_chatgpt_conversations(data)}
            
            # Detectar Claude
            claude_score = self._score_claude(data)
            if claude_score > self.conversation_patterns['claude']['confidence_threshold']:
                return 'claude', claude_score, {'structure': 'json', 'conversations_detected': self._count_claude_conversations(data)}
            
            # JSON genérico
            return 'json_generic', 0.3, {'structure': 'json'}
            
        except json.JSONDecodeError:
            return 'not_json', 0.0, {}
    
    def _detect_text_format(self, content: str) -> Tuple[str, float, Dict]:
        """Detecta formatos de texto (Cline, Markdown)"""
        # Detectar Cline/Continue
        cline_score = self._score_cline(content)
        if cline_score > self.conversation_patterns['cline']['confidence_threshold']:
            conversations = self._count_cline_conversations(content)
            return 'cline', cline_score, {
                'structure': 'markdown',
                'conversations_detected': conversations,
                'patterns_found': self._get_cline_patterns_found(content)
            }
        
        # Texto genérico
        return 'text_generic', 0.1, {'structure': 'text'}
    
    def _score_chatgpt(self, data: Any) -> float:
        """Calcula puntuación para formato ChatGPT"""
        score = 0.0
        
        # Si es lista de conversaciones
        if isinstance(data, list) and len(data) > 0:
            sample = data[0]
            if isinstance(sample, dict):
                if 'mapping' in sample: score += 0.4
                if 'id' in sample: score += 0.2
                if 'create_time' in sample: score += 0.2
                if 'title' in sample: score += 0.2
        
        # Si es conversación única
        elif isinstance(data, dict):
            if 'mapping' in data: score += 0.4
            if 'id' in data: score += 0.2
            if 'create_time' in data: score += 0.2
            if 'title' in data: score += 0.2
        
        return min(1.0, score)
    
    def _score_claude(self, data: Any) -> float:
        """Calcula puntuación para formato Claude"""
        score = 0.0
        
        if isinstance(data, list) and len(data) > 0:
            sample = data[0]
            if isinstance(sample, dict):
                if 'conversation_id' in sample: score += 0.3
                if 'name' in sample: score += 0.2
                if 'chat_messages' in sample: score += 0.3
                if 'created_at' in sample: score += 0.2
        
        return min(1.0, score)
    
    def _score_cline(self, content: str) -> float:
        """Calcula puntuación para formato Cline"""
        score = 0.0
        patterns = self.conversation_patterns['cline']['text_patterns']
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                score += 0.2
        
        return min(1.0, score)
    
    def _count_chatgpt_conversations(self, data: Any) -> int:
        """Cuenta conversaciones en formato ChatGPT"""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict) and 'mapping' in data:
            return 1
        return 0
    
    def _count_claude_conversations(self, data: Any) -> int:
        """Cuenta conversaciones en formato Claude"""
        if isinstance(data, list):
            return len(data)
        return 0
    
    def _count_cline_conversations(self, content: str) -> int:
        """Cuenta conversaciones en formato Cline"""
        # Buscar patrones de inicio de conversación
        task_patterns = [
            r'# Cline Task',
            r'# Task',
            r'## New Conversation',
            r'---\s*\n.*Human:', 
        ]
        
        conversations = 0
        for pattern in task_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            conversations = max(conversations, len(matches))
        
        # Si no hay patrones de tarea, pero hay intercambios Human/Assistant
        if conversations == 0:
            human_patterns = re.findall(r'##?\s*(Human|User):', content, re.IGNORECASE)
            if len(human_patterns) > 0:
                conversations = 1  # Al menos una conversación
        
        return max(1, conversations)  # Mínimo 1 si hay contenido
    
    def _get_cline_patterns_found(self, content: str) -> List[str]:
        """Obtiene lista de patrones encontrados en Cline"""
        patterns_found = []
        for pattern in self.conversation_patterns['cline']['text_patterns']:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                patterns_found.append(pattern)
        return patterns_found
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Procesa archivo detectando formato y extrayendo conversaciones
        """
        format_type, confidence, metadata = self.detect_format(file_path)
        
        # Procesar según formato detectado
        if format_type == 'chatgpt':
            conversations = self._process_chatgpt_file(file_path)
        elif format_type == 'claude':
            conversations = self._process_claude_file(file_path)
        elif format_type == 'cline':
            conversations = self._process_cline_file(file_path)
        else:
            conversations = []
        
        return {
            'format': format_type,
            'confidence': confidence,
            'metadata': metadata,
            'conversations': conversations,
            'total_conversations': len(conversations),
            'total_messages': sum(len(conv.get('messages', [])) for conv in conversations)
        }
    
    def _process_chatgpt_file(self, file_path: str) -> List[Dict]:
        """Procesa archivo ChatGPT"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conversations = []
        
        if isinstance(data, list):
            for i, conv_data in enumerate(data):
                processed_conv = self._process_chatgpt_conversation(conv_data, i)
                if processed_conv:
                    conversations.append(processed_conv)
        elif isinstance(data, dict):
            processed_conv = self._process_chatgpt_conversation(data, 0)
            if processed_conv:
                conversations.append(processed_conv)
        
        return conversations
    
    def _process_claude_file(self, file_path: str) -> List[Dict]:
        """Procesa archivo Claude"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conversations = []
        
        if isinstance(data, list):
            for conv_data in data:
                processed_conv = self._process_claude_conversation(conv_data)
                if processed_conv:
                    conversations.append(processed_conv)
        
        return conversations
    
    def _process_cline_file(self, file_path: str) -> List[Dict]:
        """Procesa archivo Cline/Continue"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        conversations = []
        
        # Buscar múltiples conversaciones separadas por patrones
        conversation_sections = self._split_cline_conversations(content)
        
        for i, section in enumerate(conversation_sections):
            messages = self._extract_cline_messages(section)
            if messages:
                conversations.append({
                    'id': f'cline_conv_{i+1}',
                    'title': self._extract_cline_title(section),
                    'platform': 'cline',
                    'timestamp': None,
                    'messages': messages
                })
        
        return conversations
    
    def _split_cline_conversations(self, content: str) -> List[str]:
        """Divide contenido en múltiples conversaciones"""
        # Buscar separadores de conversaciones
        separators = [
            r'\n# Cline Task',
            r'\n---+\s*\n',
            r'\n## New Conversation'
        ]
        
        sections = [content]  # Empezar con todo el contenido
        
        for separator in separators:
            new_sections = []
            for section in sections:
                parts = re.split(separator, section, flags=re.IGNORECASE | re.MULTILINE)
                new_sections.extend([part.strip() for part in parts if part.strip()])
            sections = new_sections
        
        return sections if len(sections) > 1 else [content]
    
    def _extract_cline_messages(self, content: str) -> List[Dict]:
        """Extrae mensajes de una sección Cline"""
        messages = []
        lines = content.split('\n')
        
        current_message = None
        current_content = []
        
        for line in lines:
            # Detectar inicio de mensaje humano
            if re.match(r'##?\s*(Human|User):', line, re.IGNORECASE):
                if current_message:
                    current_message['content'] = '\n'.join(current_content).strip()
                    if current_message['content']:
                        messages.append(current_message)
                
                current_message = {'role': 'user', 'content': ''}
                current_content = []
                # Extraer contenido después de "Human:"
                content_after_marker = re.sub(r'##?\s*(Human|User):\s*', '', line, flags=re.IGNORECASE)
                if content_after_marker.strip():
                    current_content.append(content_after_marker)
            
            # Detectar inicio de mensaje del asistente
            elif re.match(r'##?\s*(Assistant|AI|Claude|GPT):', line, re.IGNORECASE):
                if current_message:
                    current_message['content'] = '\n'.join(current_content).strip()
                    if current_message['content']:
                        messages.append(current_message)
                
                current_message = {'role': 'assistant', 'content': ''}
                current_content = []
                # Extraer contenido después de "Assistant:"
                content_after_marker = re.sub(r'##?\s*(Assistant|AI|Claude|GPT):\s*', '', line, flags=re.IGNORECASE)
                if content_after_marker.strip():
                    current_content.append(content_after_marker)
            
            # Contenido del mensaje actual
            elif current_message is not None:
                current_content.append(line)
            
            # Si no hay mensaje actual pero hay contenido significativo, asumir que es humano
            elif line.strip() and not re.match(r'#', line):
                if not current_message:
                    current_message = {'role': 'user', 'content': ''}
                    current_content = []
                current_content.append(line)
        
        # Añadir último mensaje
        if current_message and current_content:
            current_message['content'] = '\n'.join(current_content).strip()
            if current_message['content']:
                messages.append(current_message)
        
        return messages
    
    def _extract_cline_title(self, content: str) -> str:
        """Extrae título de una conversación Cline"""
        lines = content.split('\n')
        
        for line in lines[:10]:  # Revisar primeras 10 líneas
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
            elif line.startswith('## ') and 'task' not in line.lower():
                return line[3:].strip()
        
        # Título por defecto
        first_line = lines[0].strip() if lines else ''
        if len(first_line) > 0 and len(first_line) < 100:
            return first_line
        
        return 'Cline Conversation'
    
    def _process_chatgpt_conversation(self, conv_data: Dict, index: int) -> Dict:
        """Procesa una conversación ChatGPT individual"""
        try:
            conv_id = conv_data.get('id', f'chatgpt_conv_{index}')
            title = conv_data.get('title', f'Conversación {index + 1}')
            
            mapping = conv_data.get('mapping', {})
            messages = []
            
            for node_id, node_data in mapping.items():
                message_data = node_data.get('message')
                if not message_data:
                    continue
                
                author = message_data.get('author', {})
                role = author.get('role', 'unknown')
                
                if role not in ['user', 'assistant']:
                    continue
                
                content = message_data.get('content', {})
                parts = content.get('parts', [])
                
                text = ' '.join(str(part) for part in parts if part).strip()
                if not text:
                    continue
                
                messages.append({
                    'id': message_data.get('id', node_id),
                    'role': role,
                    'content': text,
                    'timestamp': message_data.get('create_time')
                })
            
            if messages:
                return {
                    'id': conv_id,
                    'title': title,
                    'platform': 'chatgpt',
                    'timestamp': conv_data.get('create_time'),
                    'messages': messages
                }
                
        except Exception as e:
            print(f"Error procesando conversación ChatGPT {index}: {e}")
        
        return None
    
    def _process_claude_conversation(self, conv_data: Dict) -> Dict:
        """Procesa una conversación Claude individual"""
        try:
            conv_id = conv_data.get('conversation_id', 'unknown')
            title = conv_data.get('name', 'Sin título')
            
            messages = []
            for message in conv_data.get('chat_messages', []):
                if message.get('text'):
                    messages.append({
                        'id': message.get('uuid', ''),
                        'role': 'user' if message.get('sender') == 'human' else 'assistant',
                        'content': message.get('text', ''),
                        'timestamp': message.get('created_at')
                    })
            
            if messages:
                return {
                    'id': conv_id,
                    'title': title,
                    'platform': 'claude',
                    'timestamp': conv_data.get('created_at'),
                    'messages': messages
                }
                
        except Exception as e:
            print(f"Error procesando conversación Claude: {e}")
        
        return None