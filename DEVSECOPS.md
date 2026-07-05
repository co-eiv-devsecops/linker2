# Flujo DevSecOps de Linker

Este documento describe el flujo de trabajo usado para organizar el desarrollo y las operaciones del proyecto Linker mediante GitHub Projects.

## Tablero Kanban

El tablero utiliza las siguientes columnas:

Backlog → Ready → In Progress → Code Review → Security Check → Done

## Significado de las columnas

### Backlog

Contiene las tareas identificadas para el proyecto. En esta columna pueden existir ideas, mejoras, refactorizaciones o tareas técnicas que todavía no necesariamente están listas para iniciar.

### Ready

Contiene tareas que ya cumplen la Definition of Ready. Esto significa que el equipo entiende qué se debe hacer, cuáles son los criterios de aceptación y qué condiciones deben cumplirse para comenzar el trabajo.

### In Progress

Contiene tareas que se encuentran en desarrollo, implementación o configuración.

### Code Review

Contiene tareas cuyo desarrollo inicial ya fue completado y que deben ser revisadas antes de avanzar. La revisión puede incluir código, documentación, estructura del cambio y cumplimiento de los criterios de aceptación.

### Security Check

Contiene tareas que deben pasar por una revisión básica de seguridad antes de considerarse terminadas. Esta revisión puede incluir validación de entradas, uso de consultas parametrizadas, revisión de secretos, permisos, dependencias, configuración y exposición de datos.

### Done

Contiene tareas completamente finalizadas. Una tarea solo puede llegar a Done cuando fue implementada, probada, revisada, validada en seguridad y entregada para uso real o validación por parte del usuario correspondiente.

## Definition of Ready

Una tarea está lista para comenzar cuando cumple las siguientes condiciones:

- El objetivo de la tarea está claramente definido.
- El comportamiento esperado fue entendido por el equipo.
- Los criterios de aceptación están definidos.
- Se identificaron los archivos, módulos o componentes relacionados.
- Se conocen las dependencias o restricciones principales.
- La tarea puede ser desarrollada sin requerir aclaraciones críticas adicionales.
- Existe claridad sobre cómo se validará el resultado.

La Definition of Ready no significa que la funcionalidad ya esté desarrollada. Significa que la tarea está suficientemente preparada para iniciar el trabajo de forma ordenada.

## Definition of Done

Una tarea se considera terminada cuando cumple las siguientes condiciones:

- La implementación cumple los criterios de aceptación.
- El cambio está disponible en el repositorio.
- El código o la configuración fueron revisados.
- Se realizaron pruebas manuales o automatizadas según corresponda.
- No se rompe el flujo principal de la aplicación.
- La tarea pasó por revisión de seguridad.
- La documentación fue actualizada si era necesario.
- El cambio fue desplegado, integrado o dejado disponible para que el usuario final o usuario técnico pueda utilizarlo.
- La funcionalidad, mejora o configuración ya puede ser usada en un escenario real o validado por el usuario correspondiente.

En este proyecto, Done no significa únicamente que el código fue escrito. Significa que el cambio ya fue validado y entregado como una capacidad usable.