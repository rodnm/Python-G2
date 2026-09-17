# Parte 2 - Tuples

# Crear la tupla
ages = (20, 25, 22, 30, 28)

# 1. Imprimir la tupla
print("Tupla original:", ages)

# 2. Primer y último elemento
print("Primer elemento:", ages[0])
print("Último elemento:", ages[-1])

# 3. Máximo, mínimo y número de elementos
print("Valor máximo:", max(ages))
print("Valor mínimo:", min(ages))
print("Número de elementos:", len(ages))

# 4. Intentar modificar un elemento de la tupla
# ages[0] = 99  <-- esta línea causaría un TypeError
# Las tuplas son INMUTABLES en Python: una vez creadas,
# sus elementos no pueden cambiarse. A diferencia de las listas,
# las tuplas no permiten reasignación de valores por índice.
