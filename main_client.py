from core import SimpleFTPClient

def main():
    print("=== CLIENT FTP SIMPLIFIÉ (PYTHON) ===")
    host = input("Adresse IP du serveur FTP: ") or "127.0.0.1"
    username = input("Nom d'utilisateur: ") or "ftpuser"
    password = input("Mot de passe : ")
    
    #client = SimpleFTPClient(host=host)
    client = SimpleFTPClient(host=host, port=2121)
    print("\nConnexion au serveur...")
    client.connect()
    
    if client.login(username, password):
        print("[OK] Authentification réussie.")
        
        # Boucle de navigation basique
        while True:
            print("\nRécupération de la liste des fichiers...")
            client.list_files()
            
            choix = input("Options : [1] Entrer dans un dossier | [2] Télécharger un fichier | [3] Quitter : ")
            
            if choix == "1":
                dossier = input("Nom du dossier où entrer : ")
                client.change_directory(dossier)
            elif choix == "2":
                remote_file = input("Nom du fichier à télécharger : ")
                local_file = input("Nom sous lequel l'enregistrer en local : ")
                client.download_file(remote_file, local_file)
            elif choix == "3":
                break
            else:
                print("Option invalide.")
        
        client.disconnect()
    else:
        print("[Échec] Identifiants incorrects ou refusés.")

if __name__ == "__main__":
    main()
