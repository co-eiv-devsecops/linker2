# Security Policy

## Reporte de vulnerabilidades

Si encuentras un problema de seguridad, no lo publiques en una issue abierta.
Usa primero el flujo privado de GitHub Security Advisories o el canal privado que tenga definido el equipo del repositorio.

## Que reportar

- descripcion breve del problema;
- componente afectado;
- pasos para reproducirlo;
- impacto esperado;
- evidencia tecnica relevante;
- cualquier mitigacion temporal conocida.

## Que evitar

- compartir secretos, tokens o credenciales en texto plano;
- publicar detalles explotables en un issue publico;
- mezclar un hallazgo de seguridad con una tarea funcional sin dejarlo explicitamente marcado.

## Buenas practicas

1. Minimiza la reproduccion del problema.
2. Aisla el cambio que lo corrige.
3. Verifica si requiere rotacion de secretos o revisiones de configuracion.
4. Documenta el rollback si el cambio toca despliegue o configuracion.