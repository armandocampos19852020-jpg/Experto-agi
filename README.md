# Experto-agi - Agentes IA para Automatización y Atención al Cliente

## 🚀 Automatización y Despliegue

Este proyecto implementa agentes de IA avanzados con capacidades cuánticas, automatización de procesos y APIs para monetización.

### 📋 Características Principales

- **Quantum Transformer Elite**: Modelo híbrido clásico-cuántico para procesamiento avanzado
- **Automatización**: Scripts para procesamiento de contenido y automatización de tareas
- **API REST**: FastAPI con soporte para pagos Stripe y autenticación
- **Monitoreo**: Prometheus y logging centralizado
- **Escalabilidad**: Entrenamiento distribuido con PyTorch DDP
- **CI/CD Automatizado**: GitHub Actions para deploy automático

### 🏗️ Estructura del Proyecto

```
Experto-agi/
├── hybrid_monster_train_masivo.py    # Entrenamiento distribuido
├── nim_c2_agent_api.py               # API principal
├── stripe_flask_gateway.py           # Integración Stripe
├── hybrid_quantum.py                 # Módulo cuántico
├── docker-compose.yml                # Orquestación de servicios
├── Dockerfile                        # Containerización
├── .github/workflows/deploy.yml      # CI/CD automation
├── deploy.sh                         # Script de despliegue
├── requirements.txt                  # Dependencias Python
└── prometheus.yml                    # Configuración de monitoreo
```

### 🛠️ Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/armandocampos19852020-jpg/Experto-agi.git
cd Experto-agi

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### 🐳 Despliegue con Docker

```bash
# Construir y ejecutar
docker-compose up -d

# Ver logs
docker-compose logs -f web

# Detener servicios
docker-compose down
```

### 🚢 Despliegue en Producción

```bash
# Hacer script ejecutable
chmod +x deploy.sh

# Ejecutar despliegue
ENVIRONMENT=production ./deploy.sh
```

### 📊 Monitoreo

- **API Metrics**: http://localhost:8000/metrics
- **Prometheus Dashboard**: http://localhost:9090
- **Logs**: `docker-compose logs -f web`

### 🔌 API Endpoints

```
POST   /v1/agents/train          - Entrenar agente
GET    /v1/agents/{id}           - Obtener información del agente
POST   /v1/inference/predict     - Predicción
POST   /v1/payments/checkout     - Crear sesión Stripe
GET    /health                   - Health check
GET    /metrics                  - Métricas Prometheus
```

### 🧠 Quantum Training

```bash
# Ejecutar entrenamiento distribuido
python hybrid_monster_train_masivo.py \
    --epochs 10 \
    --batch_size 64 \
    --qubits 8 \
    --lr 0.001 \
    --log_wandb true
```

### 📈 GitHub Actions CI/CD

El proyecto incluye automatización completa:

1. **Test**: Ejecuta pytest en múltiples versiones de Python
2. **Build**: Construye imagen Docker
3. **Deploy**: Despliega automáticamente a producción en pushes a main

Ver estado: https://github.com/armandocampos19852020-jpg/Experto-agi/actions

### 🔐 Configuración de Secretos

Para CI/CD, agregar en GitHub Settings → Secrets:

- `DOCKER_USERNAME`: Usuario Docker Hub
- `DOCKER_PASSWORD`: Password Docker Hub
- `DOCKER_REGISTRY`: docker.io o tu registry privado
- `DEPLOY_KEY`: SSH private key para servidor
- `DEPLOY_SERVER`: user@host para SSH

### 🌍 Despliegue en la Nube

#### Opción 1: Railway
```bash
railway init
railway up
```

#### Opción 2: Render
```bash
# Conectar repo a Render
# Auto-deploy en cada push
```

#### Opción 3: AWS EC2
```bash
# Usar docker-compose en servidor Ubuntu
chmod +x deploy.sh
ENVIRONMENT=production ./deploy.sh
```

### 📱 Aplicación Cliente

```python
import requests

BASE_URL = "http://localhost:8000"

# Crear sesión de pago
response = requests.post(
    f"{BASE_URL}/v1/payments/checkout",
    json={
        "email": "cliente@example.com",
        "product": "premium_agent",
        "price": 99.99
    }
)

checkout_url = response.json()["checkout_url"]
print(f"Redirigir a: {checkout_url}")
```

### 🤝 Contribuir

```bash
git checkout -b feature/nueva-funcionalidad
git commit -am 'Agregar nueva funcionalidad'
git push origin feature/nueva-funcionalidad
# Crear Pull Request
```

### 📝 Logs y Debugging

```bash
# Ver logs en tiempo real
docker-compose logs -f web

# Logs específicos del entrenamiento
tail -f logs/training.log

# Acceder a container
docker-compose exec web bash
```

### 💰 Monetización

- **Pagos Stripe**: Integrado en `stripe_flask_gateway.py`
- **Webhooks**: Configurados para eventos de pago
- **Planes**: Free, Pro (99/mes), Enterprise

### 🆘 Troubleshooting

**Error: `hybrid_quantum.py` no encontrado**
- Archivo ya creado en este proceso

**Error de Puerto en Uso**
```bash
docker-compose down
# o cambiar puerto en docker-compose.yml
```

**Logs de Error en API**
```bash
docker-compose logs web --tail=50
```

### 📚 Recursos

- [PyTorch Distributed](https://pytorch.org/docs/stable/distributed.html)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Stripe API](https://stripe.com/docs/api)

### 📄 Licencia

Este proyecto está bajo licencia MIT.

### 👤 Autor

**Armando Campos**
- GitHub: [@armandocampos19852020-jpg](https://github.com/armandocampos19852020-jpg)
- Email: armando.campos19852020@gmail.com

---

**¡Tu aplicación está lista para conquistar el mundo! 🌎🚀**
