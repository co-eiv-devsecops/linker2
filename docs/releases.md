# Release workflow

Este proyecto usa lanzamientos progresivos para integrar cambios pequenos de forma continua, reducir riesgo y poder apagar codigo nuevo sin revertir despliegues completos.

## Feature flags

Las funcionalidades nuevas deben entrar apagadas por defecto cuando tengan riesgo funcional o cambien el comportamiento para usuarios.

Flag actual:

| Flag | Variable de entorno | Default | Uso |
|---|---|---|---|
| `custom_alias` | `LINKER_ENABLE_CUSTOM_ALIAS` | `false` | Permite crear enlaces cortos con alias personalizado. |

Cuando `LAUNCHDARKLY_SDK_KEY` esta configurada, Linker evalua la flag remota `custom-alias` en LaunchDarkly. Si LaunchDarkly no esta configurado o no responde, la aplicacion usa `LINKER_ENABLE_CUSTOM_ALIAS` como fallback local.

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

## Activacion con LaunchDarkly

Para usar el bono de LaunchDarkly:

1. Crear una flag booleana en LaunchDarkly con key `custom-alias`.
2. Configurar el SDK key como variable de entorno, sin guardarlo en el repositorio.
3. Iniciar la aplicacion con esa variable disponible.

Ejemplo en PowerShell:

```powershell
$env:LAUNCHDARKLY_SDK_KEY = "<sdk-key>"
python app.py
```

La aplicacion evalua `custom-alias` con el contexto `linker-python`. Puede cambiarse con:

```powershell
$env:LAUNCHDARKLY_CONTEXT_KEY = "linker-python-local"
```

Si la flag remota esta activa, `alias=demo` crea `/demo`. Si esta apagada, Linker mantiene la generacion automatica de ids.

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

En este release:

- Codigo anterior: Linker siempre genera un identificador aleatorio para cada URL corta.
- Codigo nuevo: Linker permite usar un alias personalizado cuando `LINKER_ENABLE_CUSTOM_ALIAS=true`.
- Comportamiento default: la generacion aleatoria sigue activa cuando la flag esta apagada.

Flujo recomendado:

1. Mantener el comportamiento anterior como default.
2. Introducir el comportamiento nuevo detras de una flag.
3. Activar la flag progresivamente.
4. Cambiar el default solo despues de validar estabilidad.
5. Eliminar el codigo viejo en un PR separado cuando ya no sea necesario.

Plan de eliminacion gradual:

1. Desplegar el codigo nuevo con `LINKER_ENABLE_CUSTOM_ALIAS=false`.
2. Probar la funcionalidad en local y en un ambiente controlado con la flag activa.
3. Mantener monitoreo de errores y respuestas HTTP mientras la flag este activa.
4. Si falla, apagar la flag y conservar el flujo anterior sin revertir commits.
5. Si queda estable, documentar que el alias personalizado es comportamiento soportado.
6. Abrir otro PR solo si se decide retirar una ruta vieja o simplificar codigo.

No se debe borrar el comportamiento anterior en el mismo PR que introduce el comportamiento nuevo.

## Rutina de equipo para cambios continuos

Todo cambio futuro debe seguir esta rutina:

1. Definir un scope pequeno antes de escribir codigo.
2. Crear una rama corta para la funcionalidad o correccion.
3. Agregar o actualizar pruebas en el mismo cambio.
4. Usar una feature flag si el cambio modifica comportamiento visible o tiene riesgo de release.
5. Mantener el comportamiento anterior como default cuando sea posible.
6. Documentar como activar, apagar y probar la funcionalidad.
7. Incluir plan de rollback en el PR.
8. Esperar CI verde antes de hacer merge.
9. Hacer limpieza de codigo viejo en un PR separado.

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

# Lanzamiento de funcionalidades

En Linker, despliegue y lanzamiento son procesos separados.

## Diferencia entre despliegue y lanzamiento

| Proceso | Qué hace | Workflow |
|---|---|---|
| Despliegue | Instala una nueva versión de la aplicación. | `.github/workflows/linker-python-pipeline.yml` |
| Lanzamiento | Activa o desactiva una funcionalidad ya desplegada. | `.github/workflows/release_feature.yml` |

## Feature flags disponibles

| Flag | Variable local | Estado por defecto | Uso |
|---|---|---|---|
| `custom-alias` | `LINKER_ENABLE_CUSTOM_ALIAS` | `false` | Permite crear enlaces con alias personalizado. |
| `advanced-operations` | `LINKER_ENABLE_ADVANCED_OPERATIONS` | `false` | Permite usar operaciones avanzadas sobre enlaces cortos. |

## Operaciones avanzadas

La flag `advanced-operations` habilita:

```txt
HEAD /r/<id>
DELETE /r/<id>