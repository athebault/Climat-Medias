# Dictionnaires d'erreurs courantes d'OCR
"""
    Fichier permettant de mettre à jour les corrections d'OCR utilisées dans le script de validation des adresses email.
    A mettre à jour en fonction des erreurs observées dans les données.
"""

ocr_corrections = {
    # Chiffres confondus avec des lettres
    '1': 'i',  # 1 -> i (sauf dans les chiffres légitimes)
    '0': 'o',  # 0 -> o dans certains contextes
    '5': 's',  # 5 -> s
    '10': 'io',  # 10 -> io
    '01': 'oi',  # 10 -> io
    # Autres corrections possibles
    'rn': 'm',  # rn -> m
    'vv': 'w',  # vv -> w
    'conlacl': 'contact',  # conlacl -> contact
    'redacl0n': 'redaction',  # redacl0n -> redaction
    "cenlr": "centr",  # cen1r -> centr
    'cen1r': 'centr',  # cen1r -> centr
    'conlact': 'contact',  # conlact -> contact
    'contacl': 'contact',  # contacl -> contact
    "redaclion": "redaction",  # redacl10n -> redaction
    "commun%2Ccatlon": "communication",  # commun%2Ccatlon -> communication
    "aclu": "actu",  # aclu -> actu
    }