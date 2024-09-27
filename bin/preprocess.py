import sys 

fichier_entree = sys.argv[1]
fichier_sortie = sys.argv[2]


n_print=0

verbose = False

# Lecture du fichier et capture des lignes
with open(fichier_entree, 'r', encoding='utf-8') as f1:
    lignes = f1.readlines()

# Écriture des lignes capturées et de la nouvelle ligne
    with open(fichier_sortie, 'w', encoding='utf-8') as f2:
        for ligne in lignes:
            if '!$ACDC PARALLEL' in ligne:
                ligne.replace('!$ACDC PARALLEL', '!$loki parallel PARALLEL')
                
            elif '!$ACDC ]' in ligne:
                ligne.replace('!$ACDC }', '!$loki end parallel')

            f2.write(ligne)
