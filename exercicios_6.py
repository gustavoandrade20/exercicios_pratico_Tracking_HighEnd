def remover_nulos(obj):
    """
    Recebe um dicionário e remove todas as chaves cujo valor seja None ou undefined (simulado como None em Python)
    """
    return {k: v for k, v in obj.items() if v is not None}

# Exemplo de uso
dados = {
    "nome": "Maria",
    "email": None,
    "telefone": "11999998888",
    "idade": None
}

resultado = remover_nulos(dados)
print(resultado)
