# Release workflow

Este proyecto usa lanzamientos progresivos para integrar cambios pequenos de forma continua, reducir riesgo y poder apagar codigo nuevo sin revertir despliegues completos.

## Feature flags

Las funcionalidades nuevas deben entrar apagadas por defecto cuando tengan riesgo funcional o cambien el comportamiento para usuarios.

Flag actual:

| Flag | Variable de entorno | Default | Uso |
|---|---|---|---|
| `custom_alias` | `LINKER_ENABLE_CUSTOM_ALIAS` | `false` | Permite crear enlaces cortos con alias personalizado. |

Valores aceptados para activar una flag:

```bash
1
true
yes
on
enabled
```

Valores aceptados para apagar una flag:

```bash
0
false
no
off
disabled
```

## Activacion local

Para probar la funcionalidad de alias personalizados:

```bash
LINKER_ENABLE_CUSTOM_ALIAS=true python3 app.py
```

Luego enviar el alias en una peticion HTTP:

```bash
curl -i -X POST http://localhost:8080/link \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://www.python.org&alias=python-docs"
```

Si la flag esta apagada, el parametro `alias` se ignora y Linker genera un id aleatorio como antes.

## Rollout progresivo

1. Crear el cambio en una rama corta desde `main`.
2. Agregar pruebas automatizadas para el comportamiento nuevo.
3. Dejar la funcionalidad detras de una feature flag apagada por defecto.
4. Abrir un pull request pequeno y revisable.
5. Hacer merge cuando CI este verde y exista aprobacion.
6. Desplegar a produccion con la flag apagada.
7. Activar la flag primero para pruebas internas.
8. Monitorear errores, respuestas HTTP y comportamiento esperado.
9. Activar la flag para todos cuando el comportamiento sea estable.

## Rollback

Si la funcionalidad falla, se debe apagar la variable de entorno y reiniciar el servicio:

```bash
LINKER_ENABLE_CUSTOM_ALIAS=false
sudo systemctl restart linker-python
```

Esto permite volver al comportamiento anterior sin revertir el commit ni reconstruir la aplicacion.

## Desfase de codigo viejo

El codigo anterior no debe eliminarse en el mismo cambio que introduce el codigo nuevo.

Flujo recomendado:

1. Mantener el comportamiento anterior como default.
2. Introducir el comportamiento nuevo detras de una flag.
3. Activar la flag progresivamente.
4. Cambiar el default solo despues de validar estabilidad.
5. Eliminar el codigo viejo en un PR separado cuando ya no sea necesario.

## Rutina de small batch development

Cada cambio debe tener un alcance pequeno y una razon clara.

Ejemplo de secuencia para este release:

1. `feat(flags): add local feature flag reader`
2. `feat(links): guard custom aliases behind feature flag`
3. `docs(releases): document progressive rollout workflow`

Cada PR debe incluir:

- objetivo del cambio;
- flag afectada, si aplica;
- evidencia de pruebas;
- riesgo principal;
- plan de rollback.
