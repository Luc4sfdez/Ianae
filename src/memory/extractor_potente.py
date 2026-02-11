#!/usr/bin/env python3
"""
extractor_potente.py - Extractor completo con trazabilidad para IANAE
Procesa 308 JSONs de transcripciones literales y crea memoria real
"""

import json
import os
import re
from collections import defaultdict, Counter
from conceptos_lucas import ConceptosLucas
import time

class ExtractorPotente:
    def __init__(self):
        self.debug = True
        self.estadisticas = {
            'archivos_procesados': 0,
            'archivos_con_error': 0,
            'mensajes_extraidos': 0,
            'conceptos_creados': 0,
            'contextos_con_contenido': 0
        }
        
    def log(self, mensaje):
        """Log con timestamp para trazabilidad"""
        if self.debug:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {mensaje}")
    
    def extraer_conversacion_completa(self, data, archivo):
        """Extrae TODA la información útil de una conversación"""
        self.log(f"🔍 Procesando: {os.path.basename(archivo)}")
        
        info_extraida = {
            'titulo': '',
            'mensajes_humano': [],
            'mensajes_asistente': [],
            'temas_detectados': [],
            'tecnologias_mencionadas': [],
            'problemas_identificados': [],
            'soluciones_propuestas': [],
            'codigo_encontrado': [],
            'comandos_encontrados': [],
            'archivos_mencionados': [],
            'errores_discutidos': []
        }
        
        # Extraer título
        if 'title' in data:
            info_extraida['titulo'] = data['title']
            self.log(f"  📄 Título: {info_extraida['titulo']}")
        
        # Procesar mensajes
        if 'messages' in data:
            for mensaje in data['messages']:
                texto = mensaje.get('text', '')
                sender = mensaje.get('sender', '')
                
                if texto and len(texto.strip()) > 5:
                    if sender == 'human':
                        info_extraida['mensajes_humano'].append(texto)
                    elif sender == 'assistant':
                        info_extraida['mensajes_asistente'].append(texto)
                    
                    # Extraer información específica del texto
                    self._analizar_texto(texto, info_extraida)
        
        self.log(f"  📊 Extraído: {len(info_extraida['mensajes_humano'])} preguntas, {len(info_extraida['mensajes_asistente'])} respuestas")
        return info_extraida
    
    def _analizar_texto(self, texto, info):
        """Analiza un texto y extrae información específica con TRAZABILIDAD"""
        texto_lower = texto.lower()
        
        # Tecnologías (expandida para Lucas)
        tecnologias = {
            'python': r'\bpython\b',
            'javascript': r'\b(javascript|js)\b',
            'html': r'\bhtml\b',
            'css': r'\bcss\b',
            'vba': r'\bvba\b',
            'excel': r'\bexcel\b',
            'opencv': r'\bopencv\b',
            'docker': r'\bdocker\b',
            'linux': r'\blinux\b',
            'debian': r'\bdebian\b',
            'api': r'\bapi\b',
            'json': r'\bjson\b',
            'sql': r'\bsql\b',
            'tacografo': r'\btac[oó]grafo\b',
            'automatizacion': r'\bautomatizaci[oó]n\b',
            'bot': r'\bbot\b',
            'scraping': r'\bscraping\b',
            'selenium': r'\bselenium\b',
            'pandas': r'\bpandas\b',
            'numpy': r'\bnumpy\b',
            'matplotlib': r'\bmatplotlib\b'
        }
        
        for tech, patron in tecnologias.items():
            if re.search(patron, texto_lower):
                if tech not in info['tecnologias_mencionadas']:
                    info['tecnologias_mencionadas'].append(tech)
        
        # Comandos (más específicos)
        comandos_patrones = [
            r'`([^`]+)`',  # Texto entre backticks
            r'\$\s*([^\n]+)',  # Comandos shell
            r'sudo\s+([^\n]+)',  # Comandos sudo
            r'pip\s+install\s+([^\n]+)',  # Pip install
            r'npm\s+install\s+([^\n]+)',  # NPM install
            r'docker\s+([^\n]+)',  # Docker commands
        ]
        
        for patron in comandos_patrones:
            matches = re.finditer(patron, texto, re.IGNORECASE)
            for match in matches:
                comando = match.group(1).strip()
                if len(comando) > 2 and comando not in info['comandos_encontrados']:
                    info['comandos_encontrados'].append(comando)
        
        # Archivos mencionados
        archivos_patrones = [
            r'([a-zA-Z0-9_-]+\.(py|js|html|css|json|txt|csv|xlsx|pdf|docx))',
            r'([a-zA-Z0-9_-]+\.(exe|dll|bat|sh))'
        ]
        
        for patron in archivos_patrones:
            matches = re.finditer(patron, texto, re.IGNORECASE)
            for match in matches:
                archivo = match.group(0)
                if archivo not in info['archivos_mencionados']:
                    info['archivos_mencionados'].append(archivo)
        
        # Detección de problemas
        indicadores_problema = [
            'error', 'problema', 'fallo', 'no funciona', 'no va', 'ayuda',
            'exception', 'traceback', 'failed', 'broken', 'issue'
        ]
        
        for indicador in indicadores_problema:
            if indicador in texto_lower:
                # Extraer contexto del problema
                oraciones = texto.split('.')
                for oracion in oraciones:
                    if indicador in oracion.lower() and len(oracion.strip()) > 10:
                        info['problemas_identificados'].append(oracion.strip())
                        break
        
        # Detección de soluciones
        indicadores_solucion = [
            'solucion', 'resolver', 'arreglar', 'fix', 'corregir',
            'hacer', 'usar', 'utilizar', 'aplicar', 'instalar'
        ]
        
        for indicador in indicadores_solucion:
            if indicador in texto_lower:
                oraciones = texto.split('.')
                for oracion in oraciones:
                    if indicador in oracion.lower() and len(oracion.strip()) > 15:
                        info['soluciones_propuestas'].append(oracion.strip())
                        break
        
        # Código (bloques más grandes)
        codigo_patrones = [
            r'```[\w]*\n(.*?)\n```',  # Markdown code blocks
            r'(?:def|class|function|var|let|const)\s+[\w_]+',  # Definiciones
            r'import\s+[\w.,\s]+',  # Imports
            r'from\s+[\w.]+\s+import\s+[\w.,\s]+'  # From imports
        ]
        
        for patron in codigo_patrones:
            matches = re.finditer(patron, texto, re.MULTILINE | re.DOTALL)
            for match in matches:
                codigo = match.group(0).strip()
                if len(codigo) > 10:
                    info['codigo_encontrado'].append(codigo[:200])  # Primeros 200 chars
    
    def crear_conceptos_desde_conversacion(self, info, archivo, sistema):
        """Crea conceptos ricos desde información extraída"""
        conceptos_creados = 0
        base_nombre = os.path.basename(archivo).replace('.json', '')
        
        # Concepto principal de la conversación
        if info['titulo']:
            concepto_principal = self._limpiar_nombre_concepto(info['titulo'])
            contexto_principal = self._crear_contexto_rico(info)
            
            sistema.añadir_concepto_con_contexto(
                nombre=concepto_principal,
                contexto=contexto_principal,
                categoria='conversacion',
                fuente=base_nombre,
                palabras_clave=info['tecnologias_mencionadas'][:5]
            )
            conceptos_creados += 1
            self.log(f"  ✅ Concepto principal: {concepto_principal}")
        
        # Conceptos por tecnología
        for tech in info['tecnologias_mencionadas']:
            if tech not in sistema.conceptos:
                contexto_tech = self._crear_contexto_tecnologia(tech, info, archivo)
                sistema.añadir_concepto_con_contexto(
                    nombre=tech,
                    contexto=contexto_tech,
                    categoria='tecnologia',
                    fuente=base_nombre,
                    palabras_clave=[tech]
                )
                conceptos_creados += 1
                self.log(f"  🔧 Tecnología: {tech}")
        
        # Conceptos por problemas significativos
        for i, problema in enumerate(info['problemas_identificados'][:3]):  # Top 3
            if len(problema) > 30:
                concepto_problema = f"problema_{base_nombre}_{i+1}"
                sistema.añadir_concepto_con_contexto(
                    nombre=concepto_problema,
                    contexto=problema,
                    categoria='problema',
                    fuente=base_nombre,
                    palabras_clave=['problema', 'error']
                )
                conceptos_creados += 1
        
        # Actualizar estadísticas
        self.estadisticas['conceptos_creados'] += conceptos_creados
        if contexto_principal and len(contexto_principal) > 50:
            self.estadisticas['contextos_con_contenido'] += 1
        
        return conceptos_creados
    
    def _crear_contexto_rico(self, info):
        """Crea contexto completo de una conversación"""
        contexto_partes = []
        
        if info['titulo']:
            contexto_partes.append(f"TEMA: {info['titulo']}")
        
        if info['tecnologias_mencionadas']:
            contexto_partes.append(f"TECNOLOGÍAS: {', '.join(info['tecnologias_mencionadas'][:8])}")
        
        if info['problemas_identificados']:
            contexto_partes.append(f"PROBLEMAS: {info['problemas_identificados'][0][:100]}")
        
        if info['soluciones_propuestas']:
            contexto_partes.append(f"SOLUCIONES: {info['soluciones_propuestas'][0][:100]}")
        
        if info['comandos_encontrados']:
            contexto_partes.append(f"COMANDOS: {'; '.join(info['comandos_encontrados'][:3])}")
        
        if info['archivos_mencionados']:
            contexto_partes.append(f"ARCHIVOS: {', '.join(info['archivos_mencionados'][:5])}")
        
        # Agregar muestra de conversación real
        if info['mensajes_humano']:
            pregunta_ejemplo = info['mensajes_humano'][0][:150]
            contexto_partes.append(f"PREGUNTA: {pregunta_ejemplo}")
        
        if info['mensajes_asistente']:
            respuesta_ejemplo = info['mensajes_asistente'][0][:150]
            contexto_partes.append(f"RESPUESTA: {respuesta_ejemplo}")
        
        return " | ".join(contexto_partes)
    
    def _crear_contexto_tecnologia(self, tech, info, archivo):
        """Crea contexto específico para una tecnología"""
        contexto = f"Uso de {tech.upper()} en conversación {os.path.basename(archivo)}"
        
        # Agregar contexto específico
        ejemplos = []
        for texto in (info['mensajes_humano'] + info['mensajes_asistente'])[:5]:
            if tech.lower() in texto.lower():
                fragmento = texto[:100].replace('\n', ' ')
                ejemplos.append(fragmento)
        
        if ejemplos:
            contexto += f" | EJEMPLOS: {' ... '.join(ejemplos[:2])}"
        
        return contexto
    
    def _limpiar_nombre_concepto(self, nombre):
        """Limpia nombre para usar como concepto"""
        # Quitar caracteres especiales, convertir a snake_case
        limpio = re.sub(r'[^\w\s-]', '', nombre)
        limpio = re.sub(r'[-\s]+', '_', limpio)
        return limpio.lower()[:50]  # Max 50 chars
    
    def procesar_directorio(self, directorio):
        """Procesa todos los JSONs en un directorio"""
        self.log(f"🚀 INICIANDO PROCESAMIENTO DE: {directorio}")
        
        # Crear sistema
        sistema = ConceptosLucas(dim_vector=20)  # Vectores más grandes
        
        # Contar archivos
        archivos_json = []
        for root, dirs, files in os.walk(directorio):
            for file in files:
                if file.endswith('.json'):
                    archivos_json.append(os.path.join(root, file))
        
        self.log(f"📊 Encontrados {len(archivos_json)} archivos JSON")
        
        # Procesar cada archivo
        for i, archivo in enumerate(archivos_json):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extraer información
                info = self.extraer_conversacion_completa(data, archivo)
                self.estadisticas['mensajes_extraidos'] += len(info['mensajes_humano']) + len(info['mensajes_asistente'])
                
                # Crear conceptos
                conceptos = self.crear_conceptos_desde_conversacion(info, archivo, sistema)
                
                self.estadisticas['archivos_procesados'] += 1
                
                # Log de progreso cada 25 archivos
                if (i + 1) % 25 == 0:
                    self.log(f"📈 Progreso: {i+1}/{len(archivos_json)} archivos procesados")
                    self.log(f"   Conceptos creados hasta ahora: {self.estadisticas['conceptos_creados']}")
                
            except Exception as e:
                self.log(f"❌ Error en {archivo}: {e}")
                self.estadisticas['archivos_con_error'] += 1
        
        # Crear relaciones entre conceptos
        self.log("🔗 Creando relaciones entre conceptos...")
        self._crear_relaciones_inteligentes(sistema)
        
        # Guardar sistema
        if sistema.guardar_extendido('conceptos_lucas_completo.json'):
            self.log("💾 Sistema guardado en 'conceptos_lucas_completo.json'")
        
        # Mostrar estadísticas finales
        self._mostrar_estadisticas_finales(sistema)
        
        return sistema
    
    def _crear_relaciones_inteligentes(self, sistema):
        """Crea relaciones basadas en co-ocurrencia y categorías"""
        # Relaciones por categoría
        for categoria, conceptos in sistema.categorias.items():
            if len(conceptos) > 1:
                # Relacionar conceptos de la misma categoría
                for i, c1 in enumerate(conceptos):
                    for c2 in conceptos[i+1:]:
                        if c1 in sistema.conceptos and c2 in sistema.conceptos:
                            # Fuerza basada en co-ocurrencia
                            fuerza = 0.3 + (0.4 if categoria == 'tecnologia' else 0.2)
                            sistema.relacionar(c1, c2, fuerza=fuerza)
    
    def _mostrar_estadisticas_finales(self, sistema):
        """Muestra estadísticas completas del procesamiento"""
        self.log("🎉 PROCESAMIENTO COMPLETADO")
        self.log("=" * 50)
        
        print(f"📁 Archivos procesados: {self.estadisticas['archivos_procesados']}")
        print(f"❌ Archivos con error: {self.estadisticas['archivos_con_error']}")
        print(f"💬 Mensajes extraídos: {self.estadisticas['mensajes_extraidos']}")
        print(f"🧠 Conceptos creados: {self.estadisticas['conceptos_creados']}")
        print(f"📝 Contextos con contenido: {self.estadisticas['contextos_con_contenido']}")
        print(f"🔗 Relaciones creadas: {sistema.grafo.number_of_edges()}")
        
        print("\nCategorías creadas:")
        for categoria, conceptos in sistema.categorias.items():
            print(f"  📁 {categoria}: {len(conceptos)} conceptos")
        
        print(f"\n🎯 RESULTADO: Sistema con {len(sistema.conceptos)} conceptos ricos")

def main():
    """Función principal"""
    print("🧠 EXTRACTOR POTENTE PARA IANAE")
    print("=" * 50)
    
    # Directorio por defecto
    directorio = "memory/conversations_database"
    
    if not os.path.exists(directorio):
        directorio = input("📁 Introduce ruta del directorio con JSONs: ").strip()
        if not os.path.exists(directorio):
            print("❌ Directorio no encontrado")
            return
    
    # Crear extractor y procesar
    extractor = ExtractorPotente()
    sistema = extractor.procesar_directorio(directorio)
    
    if sistema and len(sistema.conceptos) > 50:
        print(f"\n🎉 ¡ÉXITO! Sistema potente creado")
        print("🔄 Para usar en IANAE:")
        print("  1. Renombra: conceptos_lucas_completo.json → conceptos_lucas_poblado.json") 
        print("  2. Reinicia IANAE")
        print("  3. ¡Disfruta de tu memoria completa!")
    else:
        print("\n❌ Procesamiento incompleto")

if __name__ == "__main__":
    main()
