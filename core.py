import socket
import re
import os

class SimpleFTPClient:
    def __init__(self, host="127.0.0.1", port=21):
        self.host = host
        self.port = port
        self.control_socket = None

    def _send_cmd(self, cmd):
        """Envoie une commande brute au serveur avec la terminaison CRLF."""
        full_cmd = f"{cmd}\r\n".encode('ascii')
        self.control_socket.sendall(full_cmd)

    def _get_resp(self):
        """Lit la réponse textuelle du serveur de contrôle."""
        resp = self.control_socket.recv(4096).decode('ascii')
        print(f"<- Serveur: {resp.strip()}")
        return resp

    def connect(self):
        """Établit la connexion initiale."""
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.connect((self.host, self.port))
        return self._get_resp()

    def login(self, username, password):
        """Gère la phase d'authentification."""
        self._send_cmd(f"USER {username}")
        resp = self._get_resp()
        
        if "331" in resp:  # Password required
            self._send_cmd(f"PASS {password}")
            resp = self._get_resp()
        
        return "230" in resp  # True si loggé avec succès

    def _enter_passive_mode(self):
        """Demande le mode passif et calcule le port de données."""
        self._send_cmd("PASV")
        resp = self._get_resp()
        
        # Extraction des octets pour calculer le port (ex: 227 Entering Passive Mode (127,0,0,1,156,72))
        match = re.search(r'\((.*?)\)', resp)
        if not match:
            raise Exception("Impossible d'activer le mode passif.")
            
        parts = match.group(1).split(',')
        p1, p2 = int(parts[4]), int(parts[5])
        data_port = (p1 * 256) + p2
        return data_port
    def list_files(self):
        """Récupère et affiche la liste des fichiers sur le serveur."""
        try:
            # 1. On passe en mode passif pour ouvrir le canal de données
            data_port = self._enter_passive_mode()
            
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((self.host, data_port))
            
            # 2. On envoie la commande LIST sur le canal de contrôle
            self._send_cmd("LIST")
            control_resp = self._get_resp()
            
            if "150" in control_resp or "125" in control_resp:
                print("\n--- Contenu du dossier distant ---")
                # 3. On lit la liste textuelle depuis le socket de données
                listing = ""
                while True:
                    data = data_socket.recv(4096)
                    if not data:
                        break
                    listing += data.decode('ascii')
                
                print(listing.strip())
                print("----------------------------------\n")
                
                data_socket.close()
                self._get_resp() # Lire le code 226 de fin
                return True
            else:
                data_socket.close()
        except Exception as e:
            print(f"[Erreur] Impossible de lister les fichiers : {e}")
        return False 
    
    def change_directory(self, folder_name):
        """Change le répertoire de travail actuel sur le serveur (équivalent de cd)."""
        try:
            self._send_cmd(f"CWD {folder_name}")
            resp = self._get_resp()
            
            if "250" in resp: # 250 Directory successfully changed
                print(f"[OK] Entré dans le dossier '{folder_name}'")
                return True
            else:
                print(f"[Erreur] Impossible d'accéder au dossier '{folder_name}'")
                return False
        except Exception as e:
            print(f"[Erreur] Échec du changement de dossier : {e}")
            return False

    def download_file(self, remote_filename, local_filename):
        """Télécharge un fichier du serveur en mode Passif."""
        try:
            # 1. Récupérer le port de données dynamique
            data_port = self._enter_passive_mode()
            
            # 2. Créer le socket de données et s'y connecter IMMÉDIATEMENT
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((self.host, data_port))
            
            # 3. Envoyer l'ordre de téléchargement sur le socket de contrôle
            self._send_cmd(f"RETR {remote_filename}")
            control_resp = self._get_resp()
            
            if "150" in control_resp or "125" in control_resp:
                # 4. Recevoir le flux binaire via le socket de données
                with open(local_filename, "wb") as f:
                    while True:
                        data = data_socket.recv(4096)
                        if not data:
                            break  # Le serveur a fermé le socket de données -> Fin du fichier
                        f.write(data)
                
                data_socket.close()
                
                # 5. Valider la bonne fin du transfert sur le canal de contrôle
                final_resp = self._get_resp()
                if "226" in final_resp:
                    print(f"[Succès] Fichier '{remote_filename}' téléchargé sous '{local_filename}'")
                    return True
            else:
                data_socket.close()
                print("[Erreur] Le serveur a refusé le transfert de données.")
        except Exception as e:
            print(f"[Erreur] Échec lors du téléchargement : {e}")
        return False
    
    def upload_file(self, local_filename, remote_filename):
        """Téléverse un fichier local vers le serveur en mode Passif."""
        try:
            # 1. Vérifier si le fichier local existe
            if not os.path.exists(local_filename):
                print(f"[Erreur] Le fichier local '{local_filename}' n'existe pas.")
                return False

            # 2. Récupérer le port de données dynamique
            data_port = self._enter_passive_mode()
            
            # 3. Créer le socket de données et s'y connecter
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((self.host, data_port))
            
            # 4. Envoyer l'ordre d'upload (STOR) sur le socket de contrôle
            self._send_cmd(f"STOR {remote_filename}")
            control_resp = self._get_resp()
            
            if "150" in control_resp or "125" in control_resp:
                # 5. Lire le fichier local et l'envoyer par blocs sur le socket de données
                with open(local_filename, "rb") as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break  # Fin du fichier local atteint
                        data_socket.sendall(chunk)
                
                # On ferme le socket pour signaler au serveur que l'envoi est terminé
                data_socket.close()
                
                # 6. Valider la confirmation du serveur
                final_resp = self._get_resp()
                if "226" in final_resp:
                    print(f"[Succès] Fichier '{local_filename}' téléversé avec succès sous '{remote_filename}'")
                    return True
            else:
                data_socket.close()
                print("[Erreur] Le serveur a refusé le téléversement.")
        except Exception as e:
            print(f"[Erreur] Échec lors du téléversement : {e}")
        return False

    def disconnect(self):
        """Ferme proprement la session."""
        if self.control_socket:
            self._send_cmd("QUIT")
            self._get_resp()
            self.control_socket.close()
            print("Déconnexion réussie.")
