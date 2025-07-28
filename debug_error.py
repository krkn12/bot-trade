import asyncio
import traceback
from core.async_api_handler import AsyncAPIHandler

async def test_api():
    try:
        print("🔍 Testando API assíncrona...")
        async with AsyncAPIHandler() as api:
            # Teste com múltiplos pares
            pares = ["SPKUSDT", "MDTUSDT", "SAHARAUSDT", "NEWTUSDT", "ASRUSDT"]
            
            print(f"📊 Testando {len(pares)} pares: {pares}")
            
            # Teste cada método individualmente
            for par in pares:
                print(f"\n--- Testando {par} ---")
                
                try:
                    preco = await api.get_price(par)
                    print(f"✅ Preço: {preco}")
                except Exception as e:
                    print(f"❌ Erro get_price: {e}")
                    traceback.print_exc()
                
                try:
                    ticker = await api.get_24h_ticker(par)
                    print(f"✅ Ticker: {ticker is not None}")
                except Exception as e:
                    print(f"❌ Erro get_24h_ticker: {e}")
                    traceback.print_exc()
                
                try:
                    klines = await api.get_klines(par, "1d", 100)
                    print(f"✅ Klines: {klines is not None}")
                except Exception as e:
                    print(f"❌ Erro get_klines: {e}")
                    traceback.print_exc()
            
            # Agora teste o gather como no bot original
            print("\n🚀 Testando asyncio.gather...")
            tasks = [api.get_price(p) for p in pares]
            tasks += [api.get_24h_ticker(p) for p in pares]
            tasks += [api.get_klines(p, "1d", 100) for p in pares]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            print(f"📊 Resultados: {len(results)}")
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Result {i}: {result}")
                else:
                    print(f"✅ Result {i}: OK")
    
    except Exception as e:
        print(f"⚠️ Erro geral: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())