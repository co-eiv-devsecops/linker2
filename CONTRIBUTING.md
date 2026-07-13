# Contributing

Gracias por colaborar con Linker. Esta guia resume como trabajar en el proyecto sin romper el flujo del equipo.

## Antes de empezar

1. Lee [README.md](./README.md), [DEVSECOPS.md](./DEVSECOPS.md) y [docs/releases.md](./docs/releases.md).
2. Crea una rama corta desde `main`.
3. Instala dependencias y valida el proyecto localmente.

Comandos útiles:

```bash
python3 -m unittest discover tests
python3 app.py
```

## Flujo de trabajo recomendado

1. Abre una issue usando la plantilla adecuada.
2. Mantén el alcance pequeno y verificable.
3. Sube cambios frecuentes y fáciles de revisar.
4. Abre el pull request cuando el cambio ya este listo para validarse.
5. Asegura que CI pase antes de pedir merge.

## Criterios de calidad

- Respeta el estilo existente del proyecto.
- Agrega o actualiza pruebas cuando cambie el comportamiento.
- No introduzcas dependencias nuevas sin justificarlas.
- Mantén la documentación actualizada si cambia el flujo de uso o despliegue.
- Evita mezclar correcciones no relacionadas en el mismo PR.

## Validación mínima

Antes de abrir un PR, verifica al menos esto:

- `python3 -m unittest discover tests`
- `python3 app.py`
- Revisa manualmente el flujo afectado si el cambio toca la interfaz o el endpoint HTTP.

## Checklist para pull requests

- [ ] La issue o tarea esta claramente descrita.
- [ ] El cambio tiene alcance pequeño.
- [ ] Se agregaron o ajustaron pruebas.
- [ ] Se actualizó documentación si hacia falta.
- [ ] Se penso en seguridad y en rollback.
- [ ] El PR explica el impacto y como validar el cambio.

## Cuando pedir ayuda

Usa [SUPPORT.md](./SUPPORT.md) para saber que información incluir cuando algo no funciona o cuando necesites apoyo del equipo.