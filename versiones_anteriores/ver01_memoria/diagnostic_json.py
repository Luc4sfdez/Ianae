# diagnostic_json.py
import json
import os

def diagnose_json_structure():
    conversations_path = "C:/IANAE/memory/conversations_database"
    
    print("🔍 DIAGNÓSTICO DE ESTRUCTURA JSON")
    print("=" * 50)
    
    files_checked = 0
    
    for filename in os.listdir(conversations_path):
        if filename.endswith('.json') and files_checked < 5:  # Solo primeros 5
            file_path = os.path.join(conversations_path, filename)
            files_checked += 1
            
            print(f"\n📁 ARCHIVO: {filename}")
            print("-" * 30)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Mostrar estructura
                print(f"Tipo: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Claves principales: {list(data.keys())}")
                    
                    # Mostrar algunas claves en detalle
                    for key in list(data.keys())[:5]:
                        value = data[key]
                        print(f"  {key}: {type(value)} - {str(value)[:100]}...")
                        
                elif isinstance(data, list):
                    print(f"Lista con {len(data)} elementos")
                    if len(data) > 0:
                        first_item = data[0]
                        print(f"Primer elemento: {type(first_item)}")
                        if isinstance(first_item, dict):
                            print(f"  Claves: {list(first_item.keys())}")
                
                # Buscar texto que contenga palabras clave
                def find_text_with_keywords(obj, path=""):
                    keywords = ['python', 'cv2', 'vba', 'lucas', 'tacógrafo']
                    
                    if isinstance(obj, str):
                        if any(keyword.lower() in obj.lower() for keyword in keywords):
                            print(f"    ✅ TEXTO CON KEYWORDS en {path}: {obj[:200]}...")
                    elif isinstance(obj, dict):
                        for k, v in obj.items():
                            find_text_with_keywords(v, f"{path}.{k}")
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj[:3]):  # Solo primeros 3
                            find_text_with_keywords(v, f"{path}[{i}]")
                
                print("\n🔍 Buscando texto con keywords:")
                find_text_with_keywords(data)
                
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    diagnose_json_structure()