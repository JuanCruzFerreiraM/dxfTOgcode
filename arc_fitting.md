# Algoritmo Paso a Paso para la Detección de Arcos (Hyper Fit)

El proceso combina una fase de gestión de datos secuencial (**Segmentación Incremental**) con el corazón del algoritmo, que es la solución de un **problema de valor propio generalizado**.

---

## Paso 0: Preprocesamiento y Estabilización (Traslado al Centroide)

Para garantizar la estabilidad numérica, es crucial centrar los datos. Esto facilita la inversión de la matriz de restricción $H$ y evita problemas de mal condicionamiento.

1. **Cálculo del Centroide ($\bar{x}, \bar{y}$):**
    Para el conjunto actual de $n$ puntos $(x_i, y_i)$, calcule:
    $$\bar{x} = \frac{1}{n} \sum x_i, \quad \bar{y} = \frac{1}{n} \sum y_i$$
2. **Traslación de Puntos:**
    Traslade todos los puntos $p_i$ restando el centroide. Utilizaremos los puntos trasladados $(x'_i, y'_i)$ en todos los cálculos de momentos:
    $$x'_i = x_i - \bar{x}, \quad y'_i = y_i - \bar{y}$$

## Paso 1: Segmentación Incremental (Detección de Subconjuntos)

Este proceso gestiona el flujo de puntos para aislar segmentos que posiblemente forman un arco.

1. **Inicio:** Un segmento candidato $S$ debe comenzar con al menos tres puntos no colineales para poder definir un círculo.
2. **Iteración:** Tome el siguiente punto $p_{n+1}$ del flujo de datos.
3. **Ajuste Temporal:** Agréguelo temporalmente al segmento $S$.
4. **Prueba de Ajuste:** Realice los Pasos 2 a 4 para calcular los parámetros $A_{\text{new}}$ del arco con el nuevo conjunto de $n+1$ puntos.
5. **Validación:** Aplique la prueba de la Distancia Aproximada (detallada en el Paso 5) para verificar si el punto $p_{n+1}$ es un *inlier*.
6. **Decisión:**
    * Si la distancia es menor que el umbral ($\text{InlierThreshold}$), el punto se acepta, el segmento $S$ se extiende, y se repite el proceso (volver al punto 2).
    * Si la distancia excede el umbral, el punto $p_{n+1}$ es un *outlier* y marca el final del arco actual. El segmento $S$ (sin $p_{n+1}$) se declara como un arco detectado, y $p_{n+1}$ se convierte en el inicio de un nuevo segmento candidato.

## Paso 2: Cálculo de la Matriz de Momentos $M$

El ajuste se basa en minimizar el error algebraico $F(A) = A^T M A$, donde $A=(A,B,C,D)^T$ es el vector de parámetros del círculo.

1. **Vector de Datos ($z'_i$):**
    Para cada punto centrado $(x'_i, y'_i)$, defina el valor auxiliar $z'_i = (x'_i)^2 + (y'_i)^2$. El vector de datos es:
    $$z'_i = (z'_i, x'_i, y'_i, 1)^T$$
2. **Matriz de Momentos ($M$):**
    La matriz $M$ (de dimensión $4\times4$) se calcula a partir de la Matriz de Datos $Z'$ (que apila los $z'_i$):
    $$M \stackrel{\text{def}}{=} \frac{1}{n} (Z')^T Z'$$
    *Composición de M:* Dado que los puntos han sido trasladados al centroide ($\bar{x}' = \bar{y}' = 0$):
    $$M = \begin{pmatrix} \overline{z'z'} & \overline{z'x'} & \overline{z'y'} & \overline{z'} \\ \overline{z'x'} & \overline{x'x'} & \overline{x'y'} & 0 \\ \overline{z'y'} & \overline{x'y'} & \overline{y'y'} & 0 \\ \overline{z'} & 0 & 0 & 1 \end{pmatrix}$$

## Paso 3: Cálculo de la Matriz de Restricción Hiperprecisa $H$

El Hyper Fit requiere una restricción cuadrática $A^T H A = 1$ para que la solución sea única y para asegurar un sesgo esencial nulo.

1. **Definición de $H$:** $H$ es una combinación lineal de las matrices de restricción de Taubin ($T$) y Pratt ($P$):
    $$H \stackrel{\text{def}}{=} 2T - P$$
2. **Matriz $P$ (Pratt):** Es una matriz constante:
    $$P = \begin{pmatrix} 0 & 0 & 0 & -2 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ -2 & 0 & 0 & 0 \end{pmatrix}$$
3. **Matriz $T$ (Taubin):** Puesto que $\bar{x}' = \bar{y}' = 0$:
    $$T = \begin{pmatrix} 4\overline{z'} & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 \end{pmatrix}$$
4. **Matriz $H$ (Hyper Fit):** Calculando $2T - P$:
    $$H = \begin{pmatrix} 8\overline{z'} & 0 & 0 & 2 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ 2 & 0 & 0 & 0 \end{pmatrix}$$

## Paso 4: Solución del Problema de Valor Propio Generalizado

El vector óptimo de parámetros $A$ se encuentra resolviendo la siguiente ecuación, que es el núcleo del ajuste algebraico:
$$M A = \eta H A$$

1. **Resolver el Sistema:** Se buscan los pares $(\eta, A)$ que satisfacen la ecuación.
2. **Selección del Parámetro $A$:** El vector $A=(A,B,C,D)^T$ que mejor se ajusta a los datos es el **vector propio generalizado asociado con el valor propio $\eta$ más pequeño que sea positivo**.

## Paso 5: Validación Estadística (Bondad de Ajuste)

Se utiliza la Distancia Cuadrada Aproximada para confirmar si el segmento es un arco "real" y si el nuevo punto $p_{n+1}$ es un *inlier*.

1. **Cálculo del Error de un Punto:**
    Para el nuevo punto centrado $x'=(x'_i, y'_i)$ y el vector $A$, el error cuadrado aproximado $\mathcal{S}(A, x')^2$ se calcula así:
    $$\mathcal{S}(A, x')^2 \approx \frac{\phi(A, x')^2}{\|\nabla\phi(A, x')\|^2}$$
    Donde $\phi(A, x') = A(x'^2 + y'^2) + Bx' + Cy' + D$ (la ecuación algebraica evaluada) y $\|\nabla\phi\|^2 = (2Ax' + B)^2 + (2Ay' + C)^2$ (el cuadrado de la magnitud del gradiente de $\phi$).
2. **Condición de Inlier:** El punto $p_{n+1}$ se acepta solo si su error (o el error máximo o medio del segmento) es menor que un umbral de ruido $\sigma_{\text{umbral}}^2$.
3. **Detección de "Arco Falso" (Sobre-aproximación):** La Distancia Cuadrada Aproximada Media $\hat{AF}_{\phi}(\alpha)$ no debe ser demasiado pequeña. Si:
    $$\hat{AF}_{\phi}(\alpha) \le \tau_1 \hat{\sigma}_S^2$$
    (donde $\tau_1$ es una constante pequeña, y $\hat{\sigma}_S^2$ es la varianza de ruido media estimada para el segmento), la hipótesis debe ser rechazada.

## Paso 6: Conversión a Parámetros Geométricos (Recuperación del Centro y Radio)

Si el arco ha sido validado, los parámetros $A=(A,B,C,D)^T$ se convierten a las propiedades geométricas.

1. **Centro (Trasladado):**
    $$a_{\text{traslado}} = -\frac{B}{2A}, \quad b_{\text{traslado}} = -\frac{C}{2A}$$
2. **Radio ($R$):**
    $$R = \sqrt{\frac{B^2 + C^2 - 4AD}{4A^2}}$$
3. **Recuperación al Sistema Original:** Si se requiere el centro en las coordenadas originales, se revierte la traslación del Paso 0:
    $$a = a_{\text{traslado}} + \bar{x}, \quad b = b_{\text{traslado}} + \bar{y}$$

---

### Resumen de la Ventaja del Hyper Fit

* **Velocidad:** Es un método **no iterativo**, lo que lo hace rápido y 100% confiable.
* **Precisión:** Posee **cero sesgo esencial** ($E(\Delta A_{\text{Hyper}}) \approx 0$). Esto resulta en la menor tasa de error cuadrático medio (MSE), minimizando el término de error más significativo (el sesgo).
