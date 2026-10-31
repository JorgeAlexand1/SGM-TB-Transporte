# Tablas del taller

## Errores encontrados

| Prueba_ID | Operacion | Tipo_Error | Entrada | Resultado_Esperado | Resultado_Observado_Inicial | Impacto | Severidad | Correccion | Estado_Final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OP-001 | division | Inconsistencia de nombres: division/div/divide | operand_1=20; operand_2=4 | 5 | 0 por rama no reconocida | Resultado matematico incorrecto | Critica | Unificar la clave interna como divide y validar divisor cero | Corregido |
| OP-002 | avg | Operacion sin cobertura de prueba suficiente | operand_1=6; operand_2=10 | 8 | Resultado no verificado por falta de prueba | Riesgo de regresion | Alta | Conservar rama avg y agregar prueba automatizada | Corregido |
| OP-003 | pow | Inconsistencia entre pow y power | operand_1=2; operand_2=3 | 8 | La API podia rechazar pow aunque el modelo usara power | La operacion no podia ejecutarse por API | Alta | Unificar la clave publica como power | Corregido |
| OP-004 | sqrt | Riesgo de raiz negativa sin validacion temprana | operand_1=-1 | Error | Error matematico si se alcanza el calculo | Excepcion no controlada | Critica | Mantener constraint para rechazar operandos negativos | Corregido |
| OP-005 | percent | Formula de porcentaje incompleta | base=200; porcentaje=15 | 30 | 3000 | Resultado diez veces mayor | Critica | Aplicar operand_1 * operand_2 / 100 | Corregido |

## PDCA

| Etapa | Actividad | Indicador | Criterio | Resultado |
| --- | --- | --- | --- | --- |
| Plan | Definir errores en las 5 operaciones nuevas | Hallazgos | 5 casos delimitados | 5 casos |
| Do | Corregir nombres, formulas y validaciones | Correcciones | 5 correcciones | 5 aplicadas |
| Check | Ejecutar las pruebas automatizadas | Fallos de pruebas | 0 fallos | 0 de 11 |
| Act | Conservar pruebas y restricciones para futuros cambios | Cobertura de operaciones | 5 de 5 | 5 de 5 |

## Six Sigma DMAIC

| Etapa | Actividad | Indicador | Criterio | Resultado |
| --- | --- | --- | --- | --- |
| Define | Resultados incorrectos o no controlados | Alcance | 5 operaciones | 5 operaciones |
| Measure | Medir frecuencia, severidad e impacto | Hallazgos | 5 hallazgos | 5; 3 criticos; 2 altos |
| Analyze | Relacionar hallazgos con causas raiz | Causas identificadas | 100% clasificados | 5 de 5 en Ishikawa |
| Improve | Corregir formulas, claves y validaciones | Correcciones | 5 correcciones | 5 aplicadas |
| Control | Repetir pruebas despues de cada cambio | Pruebas fallidas | 0 fallos | 0 de 11 |
