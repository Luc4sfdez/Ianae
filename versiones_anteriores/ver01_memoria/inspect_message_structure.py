# inspect_message_structure.py
import json
import os

def inspect_one_file_deeply():
    conversations_path = "C:/IANAE/memory/conversations_database"
    
    # Tomar un archivo que sabemos que tiene datos técnicos
    target_file = "004_vba2python 20241103_a2cd40be-1ce8-46cb-b0b9-7f3e3892fb07.json"
    file_path = os.path.join(conversations_path, target_file)
    
    print(f"🔍 INSPECCIÓN PROFUNDA DE: {target_file}")
    print("=" * 60)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("📋 ESTRUCTURA COMPLETA DEL ARCHIVO:")
    print(f"Claves principales: {list(data.keys())}")
    print()
    
    if 'messages' in data:
        print(f"📨 MESSAGES: {len(data['messages'])} mensajes")
        
        for i, message in enumerate(data['messages'][:3]):  # Solo primeros 3
            print(f"\n--- MENSAJE {i+1} ---")
            print(f"Claves del mensaje: {list(message.keys())}")
            
            for key, value in message.items():
                if isinstance(value, str):
                    preview = value[:100] + "..." if len(value) > 100 else value
                    print(f"  {key}: '{preview}'")
                else:
                    print(f"  {key}: {type(value)} - {str(value)[:50]}...")
    
    print("\n🔍 BUSCANDO CAMPOS CON TEXTO REAL:")
    
    def find_text_fields(obj, path=""):
        text_fields = []
        
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, str) and len(v.strip()) > 20:
                    text_fields.append({
                        'path': current_path,
                        'length': len(v),
                        'preview': v[:150] + "..." if len(v) > 150 else v
                    })
                elif isinstance(v, (dict, list)):
                    text_fields.extend(find_text_fields(v, current_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj[:5]):  # Solo primeros 5
                current_path = f"{path}[{i}]"
                text_fields.extend(find_text_fields(item, current_path))
        
        return text_fields
    
    text_fields = find_text_fields(data)
    
    print(f"\n📝 CAMPOS CON TEXTO SIGNIFICATIVO ({len(text_fields)} encontrados):")
    for field in text_fields[:10]:  # Top 10
        print(f"  • {field['path']} ({field['length']} chars)")
        print(f"    {field['preview']}")
        print()

if __name__ == "__main__":
    inspect_one_file_deeply()