# Machine Learning Predictor para Trading Bot
# Implementa modelos de aprendizado de máquina para prever movimentos de preço

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
import joblib
import os
from datetime import datetime

# Bibliotecas que precisam ser instaladas
# pip install scikit-learn pandas numpy joblib
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.pipeline import Pipeline
except ImportError:
    print("⚠️ Bibliotecas de ML não encontradas. Instale com: pip install scikit-learn pandas numpy joblib")

class MLPredictor:
    def __init__(self, model_dir="models", features=None, timeframes=None, janela_previsao=5, modelos_dir=None):
        # Compatibilidade com parâmetro modelos_dir (se fornecido, substitui model_dir)
        self.model_dir = modelos_dir if modelos_dir is not None else model_dir
        self.models = {}
        self.scalers = {}
        self.accuracy = {}
        self.last_training = {}
        
        # Parâmetros adicionais
        self.features = features or []
        self.timeframes = timeframes or []
        self.janela_previsao = janela_previsao
        
        # Criar diretório de modelos se não existir
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
        
        # Tentar carregar modelos existentes
        self._load_models()
    
    def _load_models(self):
        """Carrega modelos salvos anteriormente"""
        if not os.path.exists(self.model_dir):
            return
            
        for filename in os.listdir(self.model_dir):
            if filename.endswith("_model.pkl"):
                symbol = filename.split("_")[0]
                try:
                    model_path = os.path.join(self.model_dir, filename)
                    scaler_path = os.path.join(self.model_dir, f"{symbol}_scaler.pkl")
                    metadata_path = os.path.join(self.model_dir, f"{symbol}_metadata.pkl")
                    
                    self.models[symbol] = joblib.load(model_path)
                    
                    if os.path.exists(scaler_path):
                        self.scalers[symbol] = joblib.load(scaler_path)
                    
                    if os.path.exists(metadata_path):
                        metadata = joblib.load(metadata_path)
                        self.accuracy[symbol] = metadata.get('accuracy', 0)
                        self.last_training[symbol] = metadata.get('last_training', datetime.now())
                        
                    print(f"✅ Modelo carregado para {symbol} com acurácia de {self.accuracy.get(symbol, 0):.2%}")
                except Exception as e:
                    print(f"⚠️ Erro ao carregar modelo para {symbol}: {e}")
    
    def _create_features(self, prices: List[float], volumes: Optional[List[float]] = None) -> pd.DataFrame:
        """Cria features para o modelo de ML a partir dos preços e volumes"""
        if len(prices) < 100:
            raise ValueError("Necessário pelo menos 100 pontos de preço para criar features")
        
        df = pd.DataFrame({'price': prices})
        
        if volumes is not None and len(volumes) == len(prices):
            df['volume'] = volumes
        
        # Features técnicas
        # Retornos
        df['return_1'] = df['price'].pct_change(1)
        df['return_5'] = df['price'].pct_change(5)
        df['return_10'] = df['price'].pct_change(10)
        df['return_20'] = df['price'].pct_change(20)
        
        # Médias móveis
        for window in [5, 10, 20, 50]:
            df[f'ma_{window}'] = df['price'].rolling(window=window).mean()
            df[f'ma_diff_{window}'] = df['price'] - df[f'ma_{window}']
            df[f'ma_diff_pct_{window}'] = df[f'ma_diff_{window}'] / df[f'ma_{window}']
        
        # Volatilidade
        for window in [5, 10, 20]:
            df[f'volatility_{window}'] = df['return_1'].rolling(window=window).std()
        
        # Momentum
        for window in [5, 10, 20]:
            df[f'momentum_{window}'] = df['price'].diff(window)
        
        # RSI simplificado
        for window in [7, 14, 21]:
            delta = df['price'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=window).mean()
            avg_loss = loss.rolling(window=window).mean()
            rs = avg_gain / avg_loss
            df[f'rsi_{window}'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        for window in [20]:
            df[f'bb_middle_{window}'] = df['price'].rolling(window=window).mean()
            df[f'bb_std_{window}'] = df['price'].rolling(window=window).std()
            df[f'bb_upper_{window}'] = df[f'bb_middle_{window}'] + 2 * df[f'bb_std_{window}']
            df[f'bb_lower_{window}'] = df[f'bb_middle_{window}'] - 2 * df[f'bb_std_{window}']
            df[f'bb_width_{window}'] = (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}']) / df[f'bb_middle_{window}']
            df[f'bb_position_{window}'] = (df['price'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])
        
        # Volume features (se disponível)
        if 'volume' in df.columns:
            df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma_10'] = df['volume'].rolling(window=10).mean()
            df['volume_ratio_5'] = df['volume'] / df['volume_ma_5']
            df['volume_ratio_10'] = df['volume'] / df['volume_ma_10']
        
        # Remover linhas com NaN
        df = df.dropna()
        
        return df
    
    def _prepare_training_data(self, df: pd.DataFrame, target_lookahead: int = None, threshold: float = 0.005) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara dados para treinamento com target baseado em movimento futuro"""
        # Usar janela_previsao se target_lookahead não for especificado
        if target_lookahead is None:
            target_lookahead = self.janela_previsao
            
        # Criar target: 1 se o preço subir mais que threshold% em target_lookahead períodos, -1 se cair mais que threshold%, 0 caso contrário
        future_return = df['price'].pct_change(target_lookahead).shift(-target_lookahead)
        target = np.zeros(len(df))
        target[future_return > threshold] = 1  # Sinal de compra
        target[future_return < -threshold] = -1  # Sinal de venda
        
        # Remover a coluna de preço e outras colunas que não devem ser features
        features = df.drop(['price'], axis=1)
        if 'volume' in features.columns:
            features = features.drop(['volume'], axis=1)
        
        # Filtrar features se a lista de features estiver definida
        if self.features and len(self.features) > 0:
            # Manter apenas as colunas que contêm as features especificadas
            feature_cols = [col for col in features.columns if any(feature in col for feature in self.features)]
            if feature_cols:
                features = features[feature_cols]
        
        # Remover as últimas target_lookahead linhas que não têm target
        features = features.iloc[:-target_lookahead]
        target = target[:-target_lookahead]
        
        return features.values, target
    
    def train(self, symbol: str, prices: List[float], volumes: Optional[List[float]] = None, 
              force_retrain: bool = False, test_size: float = 0.2, target_lookahead: int = None) -> Dict:
        """Treina um modelo para um símbolo específico"""
        # Verificar se já existe um modelo recente e com boa acurácia
        if not force_retrain and symbol in self.models and symbol in self.last_training:
            last_train_days = (datetime.now() - self.last_training[symbol]).days
            if last_train_days < 7 and self.accuracy.get(symbol, 0) > 0.65:
                print(f"ℹ️ Usando modelo existente para {symbol} com acurácia de {self.accuracy[symbol]:.2%}")
                return {
                    'accuracy': self.accuracy[symbol],
                    'last_training': self.last_training[symbol],
                    'retrained': False
                }
        
        try:
            # Criar features
            df = self._create_features(prices, volumes)
            
            # Preparar dados de treinamento
            X, y = self._prepare_training_data(df, target_lookahead=target_lookahead)
            
            # Dividir em treino e teste
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            
            # Criar pipeline com scaler e modelo
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('model', RandomForestClassifier(n_estimators=100, random_state=42))
            ])
            
            # Treinar modelo
            pipeline.fit(X_train, y_train)
            
            # Avaliar modelo
            y_pred = pipeline.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Salvar modelo e metadados
            self.models[symbol] = pipeline
            self.scalers[symbol] = pipeline.named_steps['scaler']
            self.accuracy[symbol] = accuracy
            self.last_training[symbol] = datetime.now()
            
            # Salvar em disco
            model_path = os.path.join(self.model_dir, f"{symbol}_model.pkl")
            scaler_path = os.path.join(self.model_dir, f"{symbol}_scaler.pkl")
            metadata_path = os.path.join(self.model_dir, f"{symbol}_metadata.pkl")
            
            joblib.dump(pipeline, model_path)
            joblib.dump(pipeline.named_steps['scaler'], scaler_path)
            joblib.dump({
                'accuracy': accuracy,
                'last_training': self.last_training[symbol],
                'features': list(df.columns),
                'precision': precision_score(y_test, y_pred, average='weighted'),
                'recall': recall_score(y_test, y_pred, average='weighted'),
                'f1': f1_score(y_test, y_pred, average='weighted')
            }, metadata_path)
            
            print(f"✅ Modelo treinado para {symbol} com acurácia de {accuracy:.2%}")
            
            return {
                'accuracy': accuracy,
                'last_training': self.last_training[symbol],
                'retrained': True
            }
            
        except Exception as e:
            print(f"⚠️ Erro ao treinar modelo para {symbol}: {e}")
            return {'error': str(e)}
    
    def predict(self, symbol: str, prices: List[float], volumes: Optional[List[float]] = None) -> Dict:
        """Faz previsão para um símbolo específico"""
        if symbol not in self.models:
            return {'error': f"Modelo para {symbol} não encontrado. Treine primeiro."}
        
        try:
            # Criar features
            df = self._create_features(prices, volumes)
            
            # Usar apenas a última linha para previsão
            features = df.drop(['price'], axis=1)
            if 'volume' in features.columns:
                features = features.drop(['volume'], axis=1)
            
            # Fazer previsão
            prediction = self.models[symbol].predict(features.iloc[-1:].values)
            probabilities = self.models[symbol].predict_proba(features.iloc[-1:].values)[0]
            
            # Mapear previsão para sinal
            signal_map = {-1: 'SELL', 0: 'NEUTRAL', 1: 'BUY'}
            signal = signal_map[prediction[0]]
            
            # Calcular confiança
            confidence = max(probabilities)
            
            return {
                'signal': signal,
                'confidence': confidence,
                'prediction': int(prediction[0]),
                'probabilities': probabilities.tolist(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️ Erro ao fazer previsão para {symbol}: {e}")
            return {'error': str(e)}
    
    def get_model_info(self, symbol: str) -> Dict:
        """Retorna informações sobre o modelo de um símbolo"""
        if symbol not in self.models:
            return {'error': f"Modelo para {symbol} não encontrado"}
        
        metadata_path = os.path.join(self.model_dir, f"{symbol}_metadata.pkl")
        if os.path.exists(metadata_path):
            try:
                metadata = joblib.load(metadata_path)
                return metadata
            except Exception as e:
                return {'error': f"Erro ao carregar metadados: {e}"}
        
        return {
            'accuracy': self.accuracy.get(symbol, 0),
            'last_training': self.last_training.get(symbol, None)
        }
    
    def optimize_model(self, symbol: str, prices: List[float], volumes: Optional[List[float]] = None, target_lookahead: int = None) -> Dict:
        """Otimiza hiperparâmetros do modelo para um símbolo específico"""
        try:
            # Criar features
            df = self._create_features(prices, volumes)
            
            # Preparar dados de treinamento
            X, y = self._prepare_training_data(df, target_lookahead=target_lookahead)
            
            # Dividir em treino e teste
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Definir pipeline e parâmetros para otimização
            pipeline = Pipeline([
                ('scaler', StandardScaler()),
                ('model', RandomForestClassifier())
            ])
            
            param_grid = {
                'model__n_estimators': [50, 100, 200],
                'model__max_depth': [None, 10, 20, 30],
                'model__min_samples_split': [2, 5, 10],
                'model__min_samples_leaf': [1, 2, 4]
            }
            
            # Realizar busca em grade
            grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
            grid_search.fit(X_train, y_train)
            
            # Avaliar melhor modelo
            best_model = grid_search.best_estimator_
            y_pred = best_model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Salvar melhor modelo
            self.models[symbol] = best_model
            self.scalers[symbol] = best_model.named_steps['scaler']
            self.accuracy[symbol] = accuracy
            self.last_training[symbol] = datetime.now()
            
            # Salvar em disco
            model_path = os.path.join(self.model_dir, f"{symbol}_model.pkl")
            scaler_path = os.path.join(self.model_dir, f"{symbol}_scaler.pkl")
            metadata_path = os.path.join(self.model_dir, f"{symbol}_metadata.pkl")
            
            joblib.dump(best_model, model_path)
            joblib.dump(best_model.named_steps['scaler'], scaler_path)
            joblib.dump({
                'accuracy': accuracy,
                'last_training': self.last_training[symbol],
                'best_params': grid_search.best_params_,
                'precision': precision_score(y_test, y_pred, average='weighted'),
                'recall': recall_score(y_test, y_pred, average='weighted'),
                'f1': f1_score(y_test, y_pred, average='weighted')
            }, metadata_path)
            
            print(f"✅ Modelo otimizado para {symbol} com acurácia de {accuracy:.2%}")
            print(f"✅ Melhores parâmetros: {grid_search.best_params_}")
            
            return {
                'accuracy': accuracy,
                'best_params': grid_search.best_params_,
                'last_training': self.last_training[symbol]
            }
            
        except Exception as e:
            print(f"⚠️ Erro ao otimizar modelo para {symbol}: {e}")
            return {'error': str(e)}