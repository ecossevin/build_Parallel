# Chemin du fichier d'entrée et du fichier de sortie
fichier_entree = './src/arpege/out.F90'
fichier_sortie = 'src/arpege/out_print.F90'


n_print=0

# Lecture du fichier et capture des lignes
with open(fichier_entree, 'r', encoding='utf-8') as f1:
    lignes = f1.readlines()

# Écriture des lignes capturées et de la nouvelle ligne
    with open(fichier_sortie, 'w', encoding='utf-8') as f2:
        for ligne in lignes:
            f2.write(ligne)
            if 'CALL DR_HOOK' in ligne:
                print("found")
                n_print+=1
                f2.write('PRINT *,"apl_arpege_parallel_dbg ::: ' + str(n_print) + '"\n')
