# deep_content_analysis.py
import json
import os

def analyze_message_content():
    conversations_path = "C:/IANAE/memory/conversations_database"
    
    print("🔍 ANÁLISIS PROFUNDO DEL CONTENIDO")
    print("=" * 50)
    
    files_checked = 0
    total_messages = 0
    messages_with_content = 0
    content_lengths = []
    sample_contents = []
    
    for filename in os.listdir(conversations_path):
        if filename.endswith('.json') and files_checked < 10:  # Primeros 10 archivos
            file_path = os.path.join(conversations_path, filename)
            files_checked += 1
            
            print(f"\n📁 {filename}")
            print("-" * 30)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'messages' in data:
                    file_messages = 0
                    file_content_messages = 0
                    
                    for i, message in enumerate(data['messages'][:5]):  # Primeros 5 messages
                        total_messages += 1
                        file_messages += 1
                        
                        if 'content' in message:
                            content = message['content']
                            if isinstance(content, str):
                                content_len = len(content.strip())
                                content_lengths.append(content_len)
                                
                                if content_len > 10:
                                    messages_with_content += 1
                                    file_content_messages += 1
                                    
                                    # Guardar muestra
                                    sample_contents.append({
                                        'file': filename,
                                        'length': content_len,
                                        'content': content[:200] + "..." if len(content) > 200 else content
                                    })
                                
                                print(f"  Mensaje {i+1}: {content_len} chars")
                                if content_len > 0:
                                    preview = content[:100].replace('\n', ' ')
                                    print(f"    Preview: {preview}...")
                    
                    print(f"  Total: {file_messages} mensajes, {file_content_messages} con contenido")
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    print(f"\n📊 ESTADÍSTICAS GENERALES:")
    print(f"Files analizados: {files_checked}")
    print(f"Messages totales: {total_messages}")
    print(f"Messages con contenido: {messages_with_content}")
    
    if content_lengths:
        avg_length = sum(content_lengths) / len(content_lengths)
        max_length = max(content_lengths)
        min_length = min(content_lengths)
        
        print(f"Longitud promedio: {avg_length:.1f} chars")
        print(f"Longitud máxima: {max_length} chars")
        print(f"Longitud mínima: {min_length} chars")
    
    print(f"\n🔍 MUESTRAS DE CONTENIDO:")
    for i, sample in enumerate(sample_contents[:5]):
        print(f"{i+1}. {sample['file']} ({sample['length']} chars):")
        print(f"   {sample['content']}")
        print()

if __name__ == "__main__":
    analyze_message_content()