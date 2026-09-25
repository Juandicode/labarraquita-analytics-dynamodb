# Analytics propio para La Barraquita (Lambda + DynamoDB)

Sistema de analytics serverless, propio y sin terceros, para medir tráfico y engagement real en el sitio de producción de La Barraquita — proyecto de portfolio para roles de Cloud/DevOps.

**🔗 Endpoint ** `https://fmu7f97lj0.execute-api.us-east-2.amazonaws.com/track`
**🔗 Corriendo en:** `https://d1bsgcjseh0k7h.cloudfront.net` (sitio del [Proyecto 1](https://github.com/Juandicode/labarraquita-aws-s3-cloudfront))

> Nota: este repo contiene solo el backend (Lambda). El snippet de tracking que dispara los eventos vive en el `index.html` del repo del sitio — es una decisión deliberada de separar frontend y backend en repos distintos (ver sección de decisiones).

---

## Contexto

Los primeros tres proyectos del portfolio cubrieron hosting estático (S3 + CloudFront), cómputo serverless (Lambda + ECR) y CI/CD (GitHub Actions + Docker). Faltaba una pieza central de cualquier stack cloud real: **una base de datos NoSQL gestionada**.

Este proyecto retoma el sitio del Proyecto 1 y le suma una capa de analytics propio — sin Google Analytics ni cookies de terceros — pensado desde el diseño para eventualmente ofrecerse como producto a los clientes reales de ferreterías de mi micro-empresa.

**Por qué La Barraquita y no un sitio nuevo o datos simulados:** es tráfico genuino (autopromovido, pero real) en lugar de datos fabricados, y conecta narrativamente con el Proyecto 1 en vez de ser un ejercicio aislado.

---

## Arquitectura

```
Visitante → click/carga de página → fetch()
          → API Gateway (HTTP API, CORS habilitado)
          → Lambda (track-eventos)
          → DynamoDB (analytics-eventos)
```

- **Amazon DynamoDB**: tabla `analytics-eventos` con partition key `sitio_id` y sort key `timestamp`, más un Global Secondary Index (`evento` + `timestamp`) para poder consultar por tipo de evento sin escanear toda la tabla.
- **AWS Lambda**: función Python (`track-eventos`) sin contenedor — corre directo sobre el runtime administrado, usando `boto3` (ya incluido). Valida el request, genera el `timestamp` del lado del servidor, y escribe en DynamoDB.
- **Amazon API Gateway (HTTP API)**: expone la Lambda como endpoint público `POST /track`, con CORS configurado a nivel de API Gateway (no manejado a mano en la Lambda).
- **IAM**: rol dedicado para la Lambda con una policy inline de mínimo privilegio — permiso de `PutItem` restringido específicamente al ARN de la tabla `analytics-eventos`, nada más.

---

## Decisiones técnicas y por qué

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Partition key `sitio_id` + sort key `timestamp` | Partition key por tipo de evento | El acceso más frecuente es "todos los eventos de un sitio" — diseñar la tabla en función de cómo se consulta, no de cómo se ve "lógicamente" el dato, es el principio central de modelado en NoSQL. |
| GSI sobre `evento` + `timestamp` | Sin índice secundario, solo scan | Permite responder "¿cuántos clicks de WhatsApp hubo esta semana?" sin escanear la tabla completa — relevante quizás no hoy, pero sí cuando haya más de un sitio cargando datos. |
| Capacidad Provisioned 5/5 (no autoscaling) | On-Demand | Los primeros 25 RCU/WCU están en el **Always Free tier** de AWS (no solo los 12 meses iniciales). On-Demand no tiene techo fijo de costo; Provisioned con autoscaling apagado sí, y es imposible salir del free tier sin subirlo a mano. |
| Lambda sin contenedor (código inline) | Imagen Docker + ECR (como el Proyecto 2) | `boto3` ya viene en el runtime de Lambda — no hay dependencias externas que justifiquen un contenedor. Evita además cualquier problema de arquitectura arm64/x86_64 entre Mac (Apple Silicon) y Lambda, que sí fue un dolor de cabeza real en el Proyecto 2. |
| CORS configurado en API Gateway | CORS manejado a mano en el código de la Lambda | API Gateway ignora los headers CORS que devuelva el backend si CORS está configurado a nivel de API — manejarlo ahí es la fuente de verdad única, evita inconsistencias. |
| Repo separado del sitio (frontend/backend) | Todo en el mismo repo que `labarraquita-aws-s3-cloudfront` | Refleja cómo se organiza un proyecto cloud real: código versionado en Git por responsabilidad, infraestructura desplegada en AWS aparte. El repo del sitio no necesita saber cómo funciona el backend de analytics. |
| Origin `*` en CORS | Restringir al dominio exacto de CloudFront | Válido para esta fase de portfolio (sin dominio propio todavía). Documentado como ajuste pendiente antes de un uso productivo real con datos de clientes. |

---

## Troubleshooting real durante el proyecto

**Problema:** probando el tracking abriendo el `index.html` directo desde el disco (doble click, `file://...`), el navegador tiraba error de CORS (`No 'Access-Control-Allow-Origin' header is present`) a pesar de tener CORS configurado correctamente en API Gateway con `Access-Control-Allow-Origin: *`.

**Diagnóstico:** confirmé con `curl` que la API sí devolvía el header CORS correctamente ante un origen normal (`Origin: https://ejemplo.com`), pero **no** lo devolvía ante `Origin: null` — que es justo lo que manda el navegador cuando el archivo se abre desde `file://` en vez de servirse desde un dominio real.

**Causa raíz:** `null` como origen es un caso especial en CORS (no es un dominio real), y muchos servicios — API Gateway incluido — no lo tratan como un origen válido para hacer *match* contra `*`, por razones de seguridad. No era un bug de configuración: era una limitación esperable de probar en `file://` en vez de en un servidor real.

**Solución:** dejar de probar el tracking abriendo el archivo local, y probarlo siempre desde la URL real de CloudFront (que sí manda un origen `https://` válido). Una vez subido a producción, el tracking funcionó sin cambiar nada de la configuración.

---

## Costos

- DynamoDB: dentro del **Always Free tier** (5/5 RCU-WCU provisionados, muy por debajo del límite de 25/25 gratis para siempre)
- Lambda: dentro del free tier (bajo volumen de invocaciones)
- API Gateway (HTTP API): dentro del free tier (primer millón de requests/mes gratis)
- **Total actual: $0/mes**

---

## Próximos pasos posibles

- [ ] Restringir CORS al dominio real una vez que el sitio tenga uno propio
- [ ] Endpoint de lectura (`GET /stats`) + mini dashboard visual sobre los datos agregados
- [ ] Conectar el pipeline de CI/CD del Proyecto 3 para automatizar el deploy de esta Lambda
- [ ] Extender el esquema para soportar eventos de e-commerce (carrito, checkout) cuando el proyecto de Mercado Pago tenga tráfico real

---

## Stack

`AWS Lambda` `Amazon DynamoDB` `Amazon API Gateway (HTTP API)` `AWS IAM` `Python` `boto3`

---

*Proyecto 4 de 4 de un portfolio orientado a roles de Cloud/DevOps (AWS/Azure), construido sobre productos reales de mi micro-emprendimiento de desarrollo web.*
