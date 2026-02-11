#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IANAE CHAT CON MEMORIA v1.0
Interfaz de chat que utiliza el sistema RAG
Novelda, Alicante, España
"""

import requests
import json
from colorama import init, Fore, Style
from datetime import datetime
import os
import time

# Inicializar colorama
init()

class ChatConIANAE:
    def __init__(self):
        self.rag_url = "http://localhost:5000"
        self.session_start = datetime.now()
        self.message_count = 0
        
    def print_header(self):
        """Mostrar header del chat"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════╗
║                                                      ║
║  ██╗ █████╗ ███╗   ██╗ █████╗ ███████╗              ║
║  ██║██╔══██╗████╗  ██║██╔══██╗██╔════╝              ║
║  ██║███████║██╔██╗ ██║███████║█████╗                ║
║  ██║██╔══██║██║╚██╗██║██╔══██║██╔══╝                ║
║  ██║██║  ██║██║ ╚████║██║  ██║███████╗              ║
║  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝              ║
║                                                      ║
║     CHAT CON MEMORIA - Novelda, Alicante 🔥         ║
║                                                      ║
╚══════════════════════════════════════════════════════╝{Style.RESET_ALL}

{Fore.GREEN}🔥 IANAE con memoria persistente activada{Style.RESET_ALL}
{Fore.YELLOW}💾 Acceso a 308 conversaciones pasadas{Style.RESET_ALL}
{Fore.MAGENTA}🚀 Sesión iniciada: {self.session_start.strftime('%H:%M:%S')}{Style.RESET_ALL}

{Fore.CYAN}Comandos especiales:{Style.RESET_ALL}
  - {Fore.YELLOW}/help{Style.RESET_ALL}     → Mostrar ayuda
  - {Fore.YELLOW}/status{Style.RESET_ALL}   → Estado del sistema
  - {Fore.YELLOW}/buscar{Style.RESET_ALL}   → Solo buscar en memoria
  - {Fore.YELLOW}/salir{Style.RESET_ALL}    → Terminar chat

{Fore.GREEN}¡Pregúntale a IANAE sobre vuestros proyectos pasados!{Style.RESET_ALL}
{'='*60}
""")
    
    def check_rag_status(self):
        """Verificar si el servidor RAG está funcionando"""
        try:
            response = requests.get(f"{self.rag_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"{Fore.GREEN}✅ RAG Server: OK{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📁 Memoria: {data.get('memoria_path', 'N/A')}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}🌐 LM Studio: {data.get('lm_studio_url', 'N/A')}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}❌ RAG Server error: HTTP {response.status_code}{Style.RESET_ALL}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}❌ No se puede conectar al RAG Server en {self.rag_url}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Asegúrate de ejecutar: python rag_server.py{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}❌ Error verificando RAG: {e}{Style.RESET_ALL}")
            return False
    
    def enviar_pregunta(self, pregunta):
        """Enviar pregunta al sistema RAG + IANAE"""
        try:
            print(f"{Fore.YELLOW}🔍 Buscando en memoria...{Style.RESET_ALL}")
            
            response = requests.post(
                f"{self.rag_url}/chat",
                json={"pregunta": pregunta},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {"error": "Timeout - IANAE está tardando mucho en responder"}
        except requests.exceptions.ConnectionError:
            return {"error": "No se puede conectar al RAG Server"}
        except Exception as e:
            return {"error": str(e)}
    
    def solo_buscar_memoria(self, pregunta):
        """Solo buscar en memoria sin enviar a IANAE"""
        try:
            response = requests.post(
                f"{self.rag_url}/buscar",
                json={"pregunta": pregunta},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def mostrar_respuesta(self, data):
        """Mostrar respuesta formateada"""
        print(f"\n{Fore.MAGENTA}📊 INFORMACIÓN DE BÚSQUEDA:{Style.RESET_ALL}")
        print(f"   💬 Conversaciones encontradas: {data.get('conversaciones_encontradas', 0)}")
        print(f"   🧠 Memoria utilizada: {'Sí' if data.get('memoria_utilizada', False) else 'No'}")
        
        if 'respuesta_ianae' in data and 'error' not in data['respuesta_ianae']:
            respuesta_ianae = data['respuesta_ianae']
            
            if 'choices' in respuesta_ianae and respuesta_ianae['choices']:
                contenido = respuesta_ianae['choices'][0]['message']['content']
                print(f"\n{Fore.GREEN}🔥 IANAE:{Style.RESET_ALL}")
                print(f"{contenido}")
                
                # Mostrar estadísticas si están disponibles
                if 'usage' in respuesta_ianae:
                    usage = respuesta_ianae['usage']
                    print(f"\n{Fore.CYAN}📈 Estadísticas:")
                    print(f"   Tokens: {usage.get('total_tokens', 'N/A')}")
                    print(f"   Tiempo: {data.get('timestamp', 'N/A')[:19]}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}❌ Respuesta de IANAE vacía{Style.RESET_ALL}")
        else:
            error_msg = data.get('respuesta_ianae', {}).get('error', 'Error desconocido')
            print(f"{Fore.RED}❌ Error en IANAE: {error_msg}{Style.RESET_ALL}")
    
    def mostrar_solo_memoria(self, data):
        """Mostrar solo resultados de búsqueda en memoria"""
        print(f"\n{Fore.CYAN}🔍 RESULTADOS DE BÚSQUEDA EN MEMORIA:{Style.RESET_ALL}")
        print(f"   💬 Conversaciones encontradas: {data.get('conversaciones_encontradas', 0)}")
        
        if data.get('contexto'):
            print(f"\n{Fore.YELLOW}📄 CONTEXTO RECUPERADO:{Style.RESET_ALL}")
            contexto = data['contexto'][:1000] + "..." if len(data['contexto']) > 1000 else data['contexto']
            print(contexto)
        else:
            print(f"{Fore.RED}❌ No se encontró contexto relevante{Style.RESET_ALL}")
    
    def mostrar_ayuda(self):
        """Mostrar ayuda"""
        print(f"""
{Fore.CYAN}📖 AYUDA - IANAE CHAT CON MEMORIA{Style.RESET_ALL}

{Fore.YELLOW}Comandos especiales:{Style.RESET_ALL}
  /help     - Mostrar esta ayuda
  /status   - Estado del sistema RAG
  /buscar   - Solo buscar en memoria (sin preguntar a IANAE)
  /salir    - Terminar chat

{Fore.YELLOW}Ejemplos de preguntas:{Style.RESET_ALL}
  - ¿Recuerdas nuestros proyectos de tacógrafos?
  - ¿Qué código desarrollamos para OpenCV?
  - ¿Cuáles fueron nuestros proyectos con Python?
  - ¿Recuerdas cuando configuramos Docker?

{Fore.YELLOW}Cómo funciona:{Style.RESET_ALL}
  1. Escribes tu pregunta
  2. El sistema busca en tus 308 conversaciones pasadas
  3. Encuentra información relevante
  4. Se la pasa a IANAE como contexto
  5. IANAE responde con memoria específica

{Fore.GREEN}¡IANAE ahora tiene acceso a toda vuestra historia juntos!{Style.RESET_ALL}
""")
    
    def run(self):
        """Ejecutar chat principal"""
        self.print_header()
        
        # Verificar sistema
        if not self.check_rag_status():
            print(f"\n{Fore.RED}❌ Sistema RAG no disponible. Terminating.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.GREEN}🚀 Sistema listo. ¡Empieza a chatear con IANAE!{Style.RESET_ALL}\n")
        
        while True:
            try:
                # Input del usuario
                pregunta = input(f"{Fore.BLUE}Tú: {Style.RESET_ALL}").strip()
                
                if not pregunta:
                    continue
                
                # Comandos especiales
                if pregunta.lower() == '/salir':
                    print(f"{Fore.YELLOW}👋 ¡Hasta luego! Conversación con IANAE terminada.{Style.RESET_ALL}")
                    break
                
                elif pregunta.lower() == '/help':
                    self.mostrar_ayuda()
                    continue
                
                elif pregunta.lower() == '/status':
                    self.check_rag_status()
                    continue
                
                elif pregunta.lower().startswith('/buscar'):
                    query = pregunta[8:].strip() if len(pregunta) > 8 else input("¿Qué buscar? ")
                    if query:
                        resultado = self.solo_buscar_memoria(query)
                        if 'error' in resultado:
                            print(f"{Fore.RED}❌ Error: {resultado['error']}{Style.RESET_ALL}")
                        else:
                            self.mostrar_solo_memoria(resultado)
                    continue
                
                # Pregunta normal
                self.message_count += 1
                start_time = time.time()
                
                resultado = self.enviar_pregunta(pregunta)
                
                end_time = time.time()
                tiempo_respuesta = round(end_time - start_time, 2)
                
                if 'error' in resultado:
                    print(f"{Fore.RED}❌ Error: {resultado['error']}{Style.RESET_ALL}")
                else:
                    self.mostrar_respuesta(resultado)
                    print(f"{Fore.CYAN}⏱️  Tiempo de respuesta: {tiempo_respuesta}s{Style.RESET_ALL}")
                
                print(f"\n{'-'*60}")
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}👋 Chat interrumpido. ¡Hasta luego!{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Error inesperado: {e}{Style.RESET_ALL}")

if __name__ == '__main__':
    chat = ChatConIANAE()
    chat.run()