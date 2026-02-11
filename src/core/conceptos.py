#!/usr/bin/env python3
"""
conceptos_lucas.py - Extensión del núcleo IANAE para incluir contexto textual
Basado en nucleo.py pero añadiendo capacidades de contexto para Lucas
"""

from nucleo import ConceptosDifusos
import json
import numpy as np
from collections import defaultdict
import os

class ConceptosLucas(ConceptosDifusos):
    """
    Extensión de ConceptosDifusos que añade contexto textual y categorización
    específicamente adaptada para el universo conceptual de Lucas
    """
    
    def __init__(self, dim_vector=15):
        super().__init__(dim_vector=dim_vector)
        
        # Extensiones para contexto
        self.contextos = {}  # Almacena contexto textual de cada concepto
        self.categorias = defaultdict(list)  # Agrupa conceptos por categoría
        self.fuentes = {}  # Rastrea de qué conversación viene cada concepto
        
        # Metadatos de Lucas
        self.metadata_lucas = {
            'total_conversaciones_procesadas': 0,
            'resumenes_procesados': 0,
            'conceptos_con_contexto': 0,
            'ultima_actualizacion': None
        }
    
    def añadir_concepto_con_contexto(self, nombre, contexto="", categoria="general", 
                                   fuente="", palabras_clave=None, atributos=None):
        """
        Añade un concepto con contexto textual completo
        
        Args:
            nombre: Nombre del concepto
            contexto: Texto descriptivo del concepto
            categoria: Categoría del concepto (proyectos, tecnologias, etc.)
            fuente: Origen del concepto (archivo, conversación)
            palabras_clave: Lista de palabras clave asociadas
            atributos: Vector precomputado (opcional)
        
        Returns:
            nombre del concepto creado
        """
        # Crear concepto base
        nombre_creado = self.añadir_concepto(nombre, atributos)
        
        # Añadir contexto extendido
        self.contextos[nombre] = {
            'descripcion': contexto,
            'categoria': categoria,
            'palabras_clave': palabras_clave or [],
            'ejemplos': [],
            'problemas_relacionados': [],
            'soluciones': [],
            'codigo_relacionado': []
        }
        
        # Registrar fuente
        self.fuentes[nombre] = fuente
        
        # Categorizar
        if categoria not in self.categorias[categoria]:
            self.categorias[categoria].append(nombre)
        
        # Actualizar metadata
        self.metadata_lucas['conceptos_con_contexto'] += 1
        
        return nombre_creado
    
    def buscar_conceptos_por_contexto(self, query, umbral_similitud=0.3):
        """
        Busca conceptos basándose en similitud textual del contexto
        
        Args:
            query: Texto de búsqueda
            umbral_similitud: Umbral mínimo de similitud
            
        Returns:
            Lista de conceptos relevantes con su contexto
        """
        resultados = []
        query_lower = query.lower()
        
        for concepto, contexto_data in self.contextos.items():
            puntuacion = 0
            contexto_completo = f"{contexto_data['descripcion']} {' '.join(contexto_data['palabras_clave'])}"
            
            # Búsqueda simple por palabras
            palabras_query = query_lower.split()
            palabras_contexto = contexto_completo.lower().split()
            
            coincidencias = sum(1 for palabra in palabras_query if palabra in palabras_contexto)
            if len(palabras_query) > 0:
                puntuacion = coincidencias / len(palabras_query)
            
            if puntuacion >= umbral_similitud:
                resultados.append({
                    'concepto': concepto,
                    'puntuacion': puntuacion,
                    'contexto': contexto_data,
                    'fuente': self.fuentes.get(concepto, ''),
                    'categoria': contexto_data['categoria']
                })
        
        # Ordenar por puntuación
        resultados.sort(key=lambda x: x['puntuacion'], reverse=True)
        return resultados
    
    def generar_contexto_para_llm(self, conceptos_relevantes):
        """
        Genera contexto estructurado para enviar al LLM
        
        Args:
            conceptos_relevantes: Lista de conceptos encontrados
            
        Returns:
            String con contexto formateado para LLM
        """
        if not conceptos_relevantes:
            return "No se encontró contexto relevante."
        
        contexto_llm = "CONTEXTO RELEVANTE DE LAS CONVERSACIONES DE LUCAS:\n\n"
        
        for i, item in enumerate(conceptos_relevantes[:5]):  # Top 5
            concepto = item['concepto']
            datos = item['contexto']
            fuente = item['fuente']
            
            contexto_llm += f"## {i+1}. {concepto.upper()}\n"
            contexto_llm += f"**Categoría:** {datos['categoria']}\n"
            contexto_llm += f"**Fuente:** {fuente}\n"
            
            if datos['descripcion']:
                contexto_llm += f"**Descripción:** {datos['descripcion']}\n"
            
            if datos['palabras_clave']:
                contexto_llm += f"**Palabras clave:** {', '.join(datos['palabras_clave'])}\n"
            
            if datos['problemas_relacionados']:
                contexto_llm += f"**Problemas:** {'; '.join(datos['problemas_relacionados'])}\n"
            
            if datos['soluciones']:
                contexto_llm += f"**Soluciones:** {'; '.join(datos['soluciones'])}\n"
            
            contexto_llm += "\n---\n\n"
        
        return contexto_llm
    
    def importar_desde_resumenes_v6(self, directorio_resumenes):
        """
        Importa conceptos desde los resúmenes generados por generador_v6.py
        
        Args:
            directorio_resumenes: Ruta del directorio con resúmenes .md
            
        Returns:
            Número de conceptos importados
        """
        if not os.path.exists(directorio_resumenes):
            print(f"Directorio {directorio_resumenes} no existe")
            return 0
            
        conceptos_importados = 0
        
        # Leer todos los archivos .md
        for archivo in os.listdir(directorio_resumenes):
            if archivo.endswith('.md') and archivo != 'index.md':
                ruta_archivo = os.path.join(directorio_resumenes, archivo)
                conceptos_archivo = self._procesar_resumen_md(ruta_archivo)
                conceptos_importados += conceptos_archivo
                
        self.metadata_lucas['resumenes_procesados'] = len([f for f in os.listdir(directorio_resumenes) if f.endswith('.md')])
        self.metadata_lucas['ultima_actualizacion'] = self._timestamp_actual()
        
        print(f"✅ Importados {conceptos_importados} conceptos desde {directorio_resumenes}")
        return conceptos_importados
    
    def _procesar_resumen_md(self, ruta_archivo):
        """
        Procesa un archivo de resumen individual y extrae conceptos
        """
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            nombre_archivo = os.path.basename(ruta_archivo)
            conceptos_creados = 0
            
            # Extraer título principal
            lineas = contenido.split('\n')
            titulo = ""
            for linea in lineas:
                if linea.startswith('# '):
                    titulo = linea[2:].strip()
                    break
            
            if not titulo:
                titulo = nombre_archivo.replace('.md', '').replace('_', ' ')
            
            # Extraer palabras clave
            palabras_clave = []
            for linea in lineas:
                if '**Palabras clave:**' in linea:
                    palabras_texto = linea.split('**Palabras clave:**')[1].strip()
                    palabras_clave = [p.strip() for p in palabras_texto.split(',')]
                    break
            
            # Crear concepto principal del resumen
            concepto_principal = titulo.replace(' ', '_').lower()
            if concepto_principal not in self.conceptos:
                contexto_principal = self._extraer_contexto_principal(contenido)
                categoria = self._detectar_categoria(titulo, palabras_clave)
                
                self.añadir_concepto_con_contexto(
                    concepto_principal,
                    contexto=contexto_principal,
                    categoria=categoria,
                    fuente=nombre_archivo,
                    palabras_clave=palabras_clave
                )
                conceptos_creados += 1
            
            # Extraer conceptos de palabras clave
            for palabra in palabras_clave:
                if palabra and len(palabra) > 2:
                    concepto_palabra = palabra.replace(' ', '_').lower()
                    if concepto_palabra not in self.conceptos:
                        self.añadir_concepto_con_contexto(
                            concepto_palabra,
                            contexto=f"Concepto relacionado con {titulo}",
                            categoria="palabra_clave",
                            fuente=nombre_archivo,
                            palabras_clave=[palabra]
                        )
                        # Relacionar con concepto principal
                        self.relacionar(concepto_principal, concepto_palabra)
                        conceptos_creados += 1
            
            # Extraer problemas y soluciones
            self._extraer_problemas_soluciones(contenido, concepto_principal)
            
            # Extraer código
            self._extraer_codigo_relacionado(contenido, concepto_principal)
            
            return conceptos_creados
            
        except Exception as e:
            print(f"Error procesando {ruta_archivo}: {e}")
            return 0
    
    def _extraer_contexto_principal(self, contenido):
        """Extrae el contexto principal de un resumen"""
        # Buscar sección "Resumen del Tema" o "Puntos Principales"
        lineas = contenido.split('\n')
        contexto = []
        capturando = False
        
        for linea in lineas:
            if '## Resumen del Tema' in linea or '### Puntos Principales' in linea:
                capturando = True
                continue
            elif linea.startswith('##') and capturando:
                break
            elif capturando and linea.strip():
                if not linea.startswith('#'):
                    contexto.append(linea.strip())
        
        return ' '.join(contexto[:3])  # Primeras 3 líneas relevantes
    
    def _detectar_categoria(self, titulo, palabras_clave):
        """Detecta la categoría basándose en el título y palabras clave"""
        titulo_lower = titulo.lower()
        palabras_lower = [p.lower() for p in palabras_clave]
        
        # Categorías de Lucas
        if any(tech in titulo_lower or tech in ' '.join(palabras_lower) 
               for tech in ['python', 'javascript', 'html', 'css', 'api']):
            return 'tecnologia'
        elif any(proj in titulo_lower 
                for proj in ['proyecto', 'tacografo', 'automatizacion']):
            return 'proyecto'
        elif any(ia in titulo_lower or ia in ' '.join(palabras_lower)
                for ia in ['ia', 'inteligencia', 'llm', 'gpt']):
            return 'ia'
        elif any(dev in titulo_lower 
                for dev in ['desarrollo', 'programacion', 'codigo']):
            return 'desarrollo'
        else:
            return 'general'
    
    def _extraer_problemas_soluciones(self, contenido, concepto_principal):
        """Extrae problemas y soluciones del contenido"""
        if concepto_principal not in self.contextos:
            return
            
        lineas = contenido.split('\n')
        en_problemas = False
        problema_actual = ""
        
        for linea in lineas:
            if '## Problemas y Soluciones' in linea:
                en_problemas = True
                continue
            elif linea.startswith('##') and en_problemas:
                break
            elif en_problemas:
                if linea.startswith('### Problema'):
                    if problema_actual:
                        self.contextos[concepto_principal]['problemas_relacionados'].append(problema_actual)
                    problema_actual = linea.replace('### Problema', '').strip()
                elif linea.startswith('- ') and problema_actual:
                    solucion = linea[2:].strip()
                    self.contextos[concepto_principal]['soluciones'].append(solucion)
    
    def _extraer_codigo_relacionado(self, contenido, concepto_principal):
        """Extrae ejemplos de código del contenido"""
        if concepto_principal not in self.contextos:
            return
            
        # Buscar bloques de código ```
        import re
        bloques_codigo = re.findall(r'```(\w*)\n([\s\S]+?)\n```', contenido)
        
        for lenguaje, codigo in bloques_codigo:
            if codigo.strip():
                self.contextos[concepto_principal]['codigo_relacionado'].append({
                    'lenguaje': lenguaje or 'code',
                    'codigo': codigo.strip()[:200]  # Primeros 200 chars
                })
    
    def _timestamp_actual(self):
        """Retorna timestamp actual"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def guardar_extendido(self, ruta='conceptos_lucas.json'):
        """
        Guarda el estado incluyendo contextos y metadata de Lucas
        """
        try:
            # Obtener estado base
            estado_base = self._crear_estado_base()
            
            # Añadir extensiones
            estado_base['contextos'] = self.contextos
            estado_base['categorias'] = dict(self.categorias)
            estado_base['fuentes'] = self.fuentes
            estado_base['metadata_lucas'] = self.metadata_lucas
            
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump(estado_base, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            print(f"Error al guardar estado extendido: {e}")
            return False
    
    def _crear_estado_base(self):
        """Crea estado base compatible con el formato original"""
        return {
            'metricas': self.metricas,
            'dim_vector': self.dim_vector,
            'incertidumbre_base': self.incertidumbre_base,
            'conceptos': {
                nombre: {
                    'base': datos['base'].tolist(),
                    'actual': datos['actual'].tolist(),
                    'creado': datos['creado'],
                    'activaciones': datos['activaciones'],
                    'ultima_activacion': datos['ultima_activacion'],
                    'fuerza': datos['fuerza']
                }
                for nombre, datos in self.conceptos.items()
            },
            'relaciones': [
                {'origen': origen, 'destino': destino, 'peso': peso}
                for origen in self.relaciones
                for destino, peso in self.relaciones[origen]
            ],
            'timestamp': self._timestamp_actual()
        }
    
    @classmethod
    def cargar_extendido(cls, ruta='conceptos_lucas.json'):
        """
        Carga sistema con contextos extendidos
        """
        try:
            if not os.path.exists(ruta):
                return None
                
            with open(ruta, 'r', encoding='utf-8') as f:
                estado = json.load(f)
            
            # Crear instancia base
            sistema = cls(dim_vector=estado.get('dim_vector', 15))
            
            # Cargar estado base
            sistema.metricas = estado.get('metricas', {})
            
            # Cargar conceptos
            for nombre, datos in estado.get('conceptos', {}).items():
                base = np.array(datos['base'])
                actual = np.array(datos['actual'])
                
                sistema.conceptos[nombre] = {
                    'base': base,
                    'actual': actual,
                    'historial': [base.copy()],
                    'creado': datos.get('creado', 0),
                    'activaciones': datos.get('activaciones', 0),
                    'ultima_activacion': datos.get('ultima_activacion', 0),
                    'fuerza': datos.get('fuerza', 1.0)
                }
                sistema.grafo.add_node(nombre)
            
            # Cargar relaciones
            for rel in estado.get('relaciones', []):
                origen, destino, peso = rel['origen'], rel['destino'], rel['peso']
                sistema.relaciones[origen].append((destino, peso))
                sistema.grafo.add_edge(origen, destino, weight=peso)
            
            # Cargar extensiones
            sistema.contextos = estado.get('contextos', {})
            sistema.categorias = defaultdict(list, estado.get('categorias', {}))
            sistema.fuentes = estado.get('fuentes', {})
            sistema.metadata_lucas = estado.get('metadata_lucas', {})
            
            return sistema
            
        except Exception as e:
            print(f"Error al cargar estado extendido: {e}")
            return None

# Función de utilidad para crear sistema de Lucas
def crear_sistema_lucas_desde_resumenes(directorio_resumenes):
    """
    Crea un sistema de ConceptosLucas poblado desde resúmenes v6
    """
    print("🧠 Creando sistema de conceptos de Lucas...")
    
    sistema = ConceptosLucas(dim_vector=15)
    conceptos_importados = sistema.importar_desde_resumenes_v6(directorio_resumenes)
    
    if conceptos_importados > 0:
        print(f"✅ Sistema creado con {conceptos_importados} conceptos")
        print(f"📊 Categorías: {list(sistema.categorias.keys())}")
        
        # Guardar automáticamente
        sistema.guardar_extendido('conceptos_lucas_poblado.json')
        print("💾 Sistema guardado en 'conceptos_lucas_poblado.json'")
        
        return sistema
    else:
        print("❌ No se pudieron importar conceptos")
        return None

if __name__ == "__main__":
    # Prueba rápida
    directorio = input("Ruta del directorio con resúmenes v6: ")
    if os.path.exists(directorio):
        sistema = crear_sistema_lucas_desde_resumenes(directorio)
        if sistema:
            print("\n🎉 ¡Sistema de Lucas listo para usar!")
    else:
        print("❌ Directorio no encontrado")
