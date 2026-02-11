#!/usr/bin/env python3
"""
extractor_directo.py - Extrae conceptos directamente de los JSONs de Lucas
Bypass del generador v6 para crear IANAE con contexto inmediatamente
"""

import json
import os
from collections import defaultdict, Counter
import re
from conceptos_lucas import ConceptosLucas

def leer_json_seguro(archivo):
    """Lee un JSON de forma segura"""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error leyendo {archivo}: {e}")
        return None

def extraer_texto_de_json(data, archivo):
    """Extrae texto útil de cualquier estructura JSON"""
    textos = []
    
    def extraer_recursivo(obj, clave_padre=""):
        if isinstance(obj, dict):
            for clave, valor in obj.items():
                if isinstance(valor, str) and len(valor) > 10:
                    # Texto significativo
                    if any(palabra in clave.lower() for palabra in ['content', 'text', 'message', 'description', 'summary']):
                        textos.append(valor)
                elif isinstance(valor, (dict, list)):
                    extraer_recursivo(valor, clave)
        elif isinstance(obj, list):
            for item in obj:
                extraer_recursivo(item, clave_padre)
    
    extraer_recursivo(data)
    
    # Si no encontramos textos estructurados, tomar todo el texto del JSON
    if not textos:
        texto_completo = str(data)
        if len(texto_completo) > 50:
            textos.append(texto_completo[:1000])  # Primeros 1000 chars
    
    return textos

def extraer_conceptos_del_texto(texto, archivo):
    """Extrae conceptos clave del texto"""
    conceptos = []
    
    # Palabras técnicas comunes de Lucas
    palabras_clave_lucas = [
        'python', 'javascript', 'html', 'css', 'api', 'json', 'sql',
        'tacografo', 'automatizacion', 'opencv', 'ia', 'llm', 'gpt',
        'desarrollo', 'programacion', 'codigo', 'script', 'docker',
        'linux', 'debian', 'excel', 'vba', 'automation', 'bot',
        'web', 'scraping', 'data', 'analysis', 'machine learning'
    ]
    
    texto_lower = texto.lower()
    
    # Buscar palabras clave
    for palabra in palabras_clave_lucas:
        if palabra in texto_lower:
            conceptos.append({
                'concepto': palabra.replace(' ', '_'),
                'contexto': texto[:200],  # Primeros 200 chars como contexto
                'categoria': detectar_categoria(palabra),
                'fuente': archivo
            })
    
    # Extraer conceptos de nombres de archivo
    nombre_archivo = os.path.basename(archivo)
    conceptos_archivo = extraer_conceptos_de_filename(nombre_archivo)
    for concepto in conceptos_archivo:
        concepto['contexto'] = texto[:200]
        concepto['fuente'] = archivo
        conceptos.append(concepto)
    
    return conceptos

def extraer_conceptos_de_filename(filename):
    """Extrae conceptos del nombre del archivo"""
    conceptos = []
    
    # Limpiar nombre
    nombre_limpio = filename.replace('.json', '').replace('_', ' ')
    
    # Patrones comunes en tus archivos
    patrones = {
        r'debian|linux|ubuntu': ('debian', 'sistema_operativo'),
        r'python|py': ('python', 'programacion'),
        r'javascript|js': ('javascript', 'programacion'),
        r'excel|vba': ('excel', 'automatizacion'),
        r'tacografo|tachograph': ('tacografo', 'proyecto'),
        r'api|rest': ('api', 'desarrollo'),
        r'docker|container': ('docker', 'devops'),
        r'web|html|css': ('web_development', 'desarrollo'),
        r'automation|automatic': ('automatizacion', 'proyecto'),
        r'analysis|analys': ('analisis', 'data'),
        r'install|setup': ('instalacion', 'configuracion')
    }
    
    for patron, (concepto, categoria) in patrones.items():
        if re.search(patron, nombre_limpio, re.IGNORECASE):
            conceptos.append({
                'concepto': concepto,
                'categoria': categoria
            })
    
    return conceptos

def detectar_categoria(palabra):
    """Detecta categoría de una palabra"""
    categorias = {
        'programacion': ['python', 'javascript', 'html', 'css', 'sql'],
        'proyecto': ['tacografo', 'automatizacion', 'bot'],
        'tecnologia': ['api', 'json', 'docker', 'linux'],
        'ia': ['ia', 'llm', 'gpt', 'machine learning'],
        'desarrollo': ['desarrollo', 'programacion', 'codigo', 'web']
    }
    
    for categoria, palabras in categorias.items():
        if palabra.lower() in palabras:
            return categoria
    
    return 'general'

def procesar_conversaciones_lucas(directorio_json):
    """Procesa todas las conversaciones de Lucas y crea sistema de conceptos"""
    print(f"🔍 Procesando conversaciones en: {directorio_json}")
    
    # Crear sistema de conceptos
    sistema = ConceptosLucas(dim_vector=15)
    
    # Contadores
    archivos_procesados = 0
    conceptos_totales = 0
    errores = 0
    
    # Procesar todos los JSONs
    for root, dirs, files in os.walk(directorio_json):
        for file in files:
            if file.endswith('.json'):
                archivo_completo = os.path.join(root, file)
                
                # Leer JSON
                data = leer_json_seguro(archivo_completo)
                if data is None:
                    errores += 1
                    continue
                
                # Extraer textos
                textos = extraer_texto_de_json(data, archivo_completo)
                
                # Procesar cada texto
                for texto in textos:
                    conceptos = extraer_conceptos_del_texto(texto, archivo_completo)
                    
                    # Añadir conceptos al sistema
                    for concepto_data in conceptos:
                        nombre = concepto_data['concepto']
                        contexto = concepto_data['contexto']
                        categoria = concepto_data['categoria']
                        fuente = concepto_data['fuente']
                        
                        # Evitar duplicados
                        if nombre not in sistema.conceptos:
                            sistema.añadir_concepto_con_contexto(
                                nombre=nombre,
                                contexto=contexto,
                                categoria=categoria,
                                fuente=os.path.basename(fuente),
                                palabras_clave=[nombre]
                            )
                            conceptos_totales += 1
                
                archivos_procesados += 1
                if archivos_procesados % 50 == 0:
                    print(f"📊 Procesados {archivos_procesados} archivos...")
    
    print(f"\n✅ PROCESAMIENTO COMPLETADO:")
    print(f"📁 Archivos procesados: {archivos_procesados}")
    print(f"🧠 Conceptos extraídos: {conceptos_totales}")
    print(f"❌ Errores: {errores}")
    
    # Crear algunas relaciones básicas
    print("🔗 Creando relaciones entre conceptos...")
    crear_relaciones_basicas(sistema)
    
    # Guardar sistema
    if sistema.guardar_extendido('conceptos_lucas_poblado.json'):
        print("💾 Sistema guardado en 'conceptos_lucas_poblado.json'")
    
    return sistema

def crear_relaciones_basicas(sistema):
    """Crea relaciones básicas entre conceptos relacionados"""
    # Relaciones obvias para Lucas
    relaciones = [
        ('python', 'programacion'),
        ('javascript', 'programacion'),
        ('tacografo', 'proyecto'),
        ('automatizacion', 'python'),
        ('docker', 'desarrollo'),
        ('api', 'desarrollo'),
        ('linux', 'sistema_operativo'),
        ('excel', 'automatizacion'),
        ('ia', 'python'),
        ('web_development', 'javascript')
    ]
    
    for concepto1, concepto2 in relaciones:
        if concepto1 in sistema.conceptos and concepto2 in sistema.conceptos:
            sistema.relacionar(concepto1, concepto2)

def main():
    """Función principal"""
    print("🧠 EXTRACTOR DIRECTO PARA IANAE")
    print("=" * 40)
    
    # Directorio con conversaciones
    directorio = "memory/conversations_database"
    
    if not os.path.exists(directorio):
        directorio = input("📁 Introduce ruta del directorio con JSONs: ").strip()
        if not os.path.exists(directorio):
            print("❌ Directorio no encontrado")
            return
    
    # Contar JSONs
    json_count = 0
    for root, dirs, files in os.walk(directorio):
        json_count += len([f for f in files if f.endswith('.json')])
    
    print(f"📊 Encontrados {json_count} archivos JSON")
    
    if json_count == 0:
        print("❌ No hay archivos JSON para procesar")
        return
    
    # Procesar
    sistema = procesar_conversaciones_lucas(directorio)
    
    if sistema and len(sistema.conceptos) > 0:
        print(f"\n🎉 ¡ÉXITO! Sistema creado con {len(sistema.conceptos)} conceptos")
        print("🚀 Ahora puedes reiniciar IANAE para usar el contexto")
        print("\nCategorías encontradas:")
        for categoria, conceptos in sistema.categorias.items():
            print(f"  📁 {categoria}: {len(conceptos)} conceptos")
    else:
        print("❌ No se pudieron crear conceptos")

if __name__ == "__main__":
    main()
