#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IANAE RAG SERVER v1.0
Motor de búsqueda y recuperación de memoria para IANAE
Novelda, Alicante, España
"""

import json
import os
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import re
from colorama import init, Fore, Style

# Inicializar colorama para colores en terminal
init()

class IANAEMemoryRAG:
    def __init__(self, config_path="config.json"):
        """Inicializar sistema RAG de IANAE"""
        self.load_config(config_path)
        self.setup_logging()
        
    def load_config(self, config_path):
        """Cargar configuración"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✅ Configuración cargada desde {config_path}")
        except Exception as e:
            print(f"❌ Error cargando config: {e}")
            # Configuración por defecto
            self.config = {
                "memory_path": "C:/IANAE/memory/conversations_database/",
                "lm_studio_url": "http://localhost:1234",
                "max_conversations": 3,
                "keywords_weight": {"tacografo": 10, "python": 8, "lucas": 7}
            }
    
    def setup_logging(self):
        """Configurar logging"""
        self.log_file = f"logs/rag_log_{datetime.now().strftime('%Y%m%d')}.txt"
        os.makedirs("logs", exist_ok=True)
        
    def log(self, message):
        """Escribir log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Consola con colores
        if "✅" in message:
            print(f"{Fore.GREEN}{log_entry.strip()}{Style.RESET_ALL}")
        elif "❌" in message:
            print(f"{Fore.RED}{log_entry.strip()}{Style.RESET_ALL}")
        elif "🔍" in message:
            print(f"{Fore.YELLOW}{log_entry.strip()}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}{log_entry.strip()}{Style.RESET_ALL}")
        
        # Archivo
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except:
            pass
    
    def buscar_conversaciones(self, pregunta):
        """Buscar conversaciones relevantes basadas en la pregunta"""
        self.log(f"🔍 Buscando memoria para: '{pregunta}'")
        
        # Extraer keywords de la pregunta
        keywords = self.extract_keywords(pregunta)
        self.log(f"📝 Keywords extraídas: {keywords}")
        
        conversaciones_relevantes = []
        memory_path = self.config["memory_path"]
        
        if not os.path.exists(memory_path):
            self.log(f"❌ Ruta de memoria no existe: {memory_path}")
            return []
        
        # Buscar en todos los archivos JSON
        archivos_procesados = 0
        for archivo in os.listdir(memory_path):
            if archivo.endswith('.json') and not archivo.startswith('000_'):
                try:
                    archivo_path = os.path.join(memory_path, archivo)
                    with open(archivo_path, 'r', encoding='utf-8') as f:
                        conv = json.load(f)
                    
                    # Calcular relevancia
                    score = self.calculate_relevance_score(conv, keywords)
                    
                    if score > 0:
                        conv['relevance_score'] = score
                        conv['archivo'] = archivo
                        conversaciones_relevantes.append(conv)
                        
                    archivos_procesados += 1
                    
                except Exception as e:
                    self.log(f"⚠️ Error procesando {archivo}: {e}")
                    continue
        
        # Ordenar por relevancia
        conversaciones_relevantes.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Limitar resultados
        max_conv = self.config.get("max_conversations", 3)
        conversaciones_relevantes = conversaciones_relevantes[:max_conv]
        
        self.log(f"✅ Procesados {archivos_procesados} archivos, {len(conversaciones_relevantes)} relevantes")
        
        return conversaciones_relevantes
    
    def extract_keywords(self, texto):
        """Extraer palabras clave del texto"""
        # Limpiar texto
        texto_limpio = re.sub(r'[^\w\s]', ' ', texto.lower())
        palabras = texto_limpio.split()
        
        # Filtrar palabras cortas y comunes
        stop_words = {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las'}
        keywords = [p for p in palabras if len(p) > 2 and p not in stop_words]
        
        return keywords
    
    def calculate_relevance_score(self, conversacion, keywords):
        """Calcular score de relevancia de una conversación"""
        score = 0
        weights = self.config.get("keywords_weight", {})
        
        # Textos donde buscar
        titulo = conversacion.get('title', '').lower()
        mensajes_texto = ""
        
        # Extraer texto de mensajes
        if 'messages' in conversacion and conversacion['messages']:
            for msg in conversacion['messages'][:5]:  # Solo primeros 5 mensajes
                if isinstance(msg, dict) and 'text' in msg:
                    mensajes_texto += msg['text'].lower() + " "
        
        texto_completo = titulo + " " + mensajes_texto
        
        # Calcular score por keyword
        for keyword in keywords:
            count_titulo = titulo.count(keyword)
            count_mensajes = mensajes_texto.count(keyword)
            
            # Score base
            keyword_score = count_titulo * 5 + count_mensajes * 2
            
            # Aplicar peso específico si existe
            if keyword in weights:
                keyword_score *= weights[keyword]
            
            score += keyword_score
        
        return score
    
    def construir_contexto_memoria(self, conversaciones):
        """Construir contexto de memoria para enviar a IANAE"""
        if not conversaciones:
            return "No se encontraron conversaciones relevantes en la memoria."
        
        contexto = "MEMORIA RECUPERADA DE CONVERSACIONES PASADAS:\n"
        contexto += "=" * 50 + "\n\n"
        
        for i, conv in enumerate(conversaciones, 1):
            contexto += f"CONVERSACIÓN {i}: {conv.get('title', 'Sin título')}\n"
            contexto += f"Fecha: {conv.get('created_at', 'Desconocida')}\n"
            contexto += f"Relevancia: {conv.get('relevance_score', 0)}\n"
            contexto += f"Archivo: {conv.get('archivo', 'N/A')}\n"
            
            # Añadir algunos mensajes clave
            if 'messages' in conv and conv['messages']:
                contexto += "MENSAJES CLAVE:\n"
                max_msgs = self.config.get("max_messages_per_conversation", 3)
                
                for msg in conv['messages'][:max_msgs]:
                    if isinstance(msg, dict) and 'text' in msg and msg['text'].strip():
                        sender = msg.get('sender', 'Desconocido')
                        texto = msg['text'][:200] + "..." if len(msg['text']) > 200 else msg['text']
                        contexto += f"  [{sender}]: {texto}\n"
            
            contexto += "\n" + "-" * 40 + "\n\n"
        
        return contexto
    
    def enviar_a_lm_studio(self, prompt_completo):
        """Enviar prompt con memoria a LM Studio"""
        try:
            url = f"{self.config['lm_studio_url']}/v1/chat/completions"
            
            payload = {
                "messages": [
                    {"role": "user", "content": prompt_completo}
                ],
                "temperature": 0.75,
                "max_tokens": 2048
            }
            
            self.log(f"📡 Enviando request a LM Studio: {url}")
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                self.log("✅ Respuesta recibida de LM Studio")
                return response.json()
            else:
                self.log(f"❌ Error HTTP {response.status_code}: {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            self.log("❌ No se puede conectar a LM Studio. ¿Está ejecutándose con API habilitada?")
            return {"error": "Conexión fallida - Verificar LM Studio API"}
        except Exception as e:
            self.log(f"❌ Error enviando a LM Studio: {e}")
            return {"error": str(e)}

# Crear instancia global
rag_system = IANAEMemoryRAG()

# Flask app
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "memoria_path": rag_system.config["memory_path"],
        "lm_studio_url": rag_system.config["lm_studio_url"]
    })

@app.route('/buscar', methods=['POST'])
def buscar_memoria():
    """Endpoint para buscar en memoria sin enviar a LM Studio"""
    try:
        data = request.json
        pregunta = data.get('pregunta', '')
        
        if not pregunta:
            return jsonify({"error": "Pregunta vacía"}), 400
        
        conversaciones = rag_system.buscar_conversaciones(pregunta)
        contexto = rag_system.construir_contexto_memoria(conversaciones)
        
        return jsonify({
            "pregunta": pregunta,
            "conversaciones_encontradas": len(conversaciones),
            "contexto": contexto,
            "conversaciones": conversaciones
        })
        
    except Exception as e:
        rag_system.log(f"❌ Error en /buscar: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat_con_memoria():
    """Endpoint principal - Buscar memoria y enviar a IANAE"""
    try:
        data = request.json
        pregunta = data.get('pregunta', '')
        
        if not pregunta:
            return jsonify({"error": "Pregunta vacía"}), 400
        
        rag_system.log(f"🎯 Nueva consulta: {pregunta}")
        
        # Buscar en memoria
        conversaciones = rag_system.buscar_conversaciones(pregunta)
        contexto_memoria = rag_system.construir_contexto_memoria(conversaciones)
        
        # Construir prompt completo
        prompt_completo = f"""
{contexto_memoria}

PREGUNTA ACTUAL DE LUCAS: {pregunta}

INSTRUCCIONES PARA IANAE:
- Usa la memoria recuperada para responder con contexto específico
- Si hay información relevante en la memoria, relaciónala con la pregunta
- Mantén tu personalidad característica (emojis, entusiasmo)
- Si no hay memoria relevante, responde normalmente pero menciona que no encontraste referencias específicas
"""
        
        # Enviar a LM Studio
        respuesta_lm = rag_system.enviar_a_lm_studio(prompt_completo)
        
        # Construir respuesta
        resultado = {
            "pregunta": pregunta,
            "conversaciones_encontradas": len(conversaciones),
            "memoria_utilizada": len(contexto_memoria) > 100,
            "respuesta_ianae": respuesta_lm,
            "timestamp": datetime.now().isoformat()
        }
        
        if 'error' not in respuesta_lm:
            rag_system.log("✅ Consulta completada exitosamente")
        
        return jsonify(resultado)
        
    except Exception as e:
        rag_system.log(f"❌ Error en /chat: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"""
🔥 IANAE RAG SERVER INICIANDO...
================================

📁 Memoria: {rag_system.config['memory_path']}
🌐 LM Studio: {rag_system.config['lm_studio_url']}
🔧 Puerto RAG: {rag_system.config.get('rag_server_port', 5000)}

💡 Endpoints disponibles:
   GET  /health - Estado del sistema
   POST /buscar - Solo buscar en memoria
   POST /chat   - Chat completo con IANAE

🚀 Iniciando servidor...
""")
    
    rag_system.log("🔥 IANAE RAG Server iniciado")
    
    port = rag_system.config.get('rag_server_port', 5000)
    app.run(host='0.0.0.0', port=port, debug=False)