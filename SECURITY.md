# Security Policy

## Reporte de vulnerabilidades

Si encuentras un problema de seguridad, no lo publiques en una issue abierta.
Usa primero el flujo privado de GitHub Security Advisories o el canal privado que tenga definido el equipo del repositorio.

## Qué reportar

- descripción breve del problema;
- componente afectado;
- pasos para reproducirlo;
- impacto esperado;
- evidencia técnica relevante;
- cualquier mitigación temporal conocida.

## Qué evitar

- compartir secretos, tokens o credenciales en texto plano;
- publicar detalles explotables en un issue público;
- mezclar un hallazgo de seguridad con una tarea funcional sin dejarlo explícitamente marcado.

## Buenas prácticas

1. Minimiza la reproducción del problema.
2. Aisla el cambio que lo corrige.
3. Verifica si requiere rotación de secretos o revisiones de configuración.
4. Documenta el rollback si el cambio toca despliegue o configuración.