#!/usr/bin/env python3
"""
Script para executar o Trading Bot corrigido
"""

import sys
import os
import logging

def check_dependencies():
    """Verifica se as dependências básicas estão disponíveis"""
    missing = []
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    try:
        import aiohttp
    except ImportError:
        missing.append("aiohttp")
    
    return missing

def main():
    print("🚀 Iniciando Trading Bot Corrigido...")
    print("=" * 50)
    
    # Verificar dependências
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ Dependências faltando: {', '.join(missing_deps)}")
        print("💡 Execute: pip3 install --break-system-packages requests aiohttp python-dotenv")
        return 1
    
    print("✅ Dependências básicas verificadas")
    
    # Verificar se arquivos corrigidos existem
    required_files = [
        "config_fixed.py",
        "binance_api_fixed.py", 
        "trade_bot_fixed.py"
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    if missing_files:
        print(f"❌ Arquivos faltando: {', '.join(missing_files)}")
        return 1
    
    print("✅ Arquivos corrigidos encontrados")
    
    try:
        # Importar e executar o bot corrigido
        from trade_bot_fixed import main as bot_main
        
        print("🤖 Iniciando bot em modo corrigido...")
        print("⚠️ Pressione Ctrl+C para parar")
        print("=" * 50)
        
        bot_main()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário")
        return 0
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        logging.exception("Erro detalhado:")
        return 1

if __name__ == "__main__":
    sys.exit(main())