import tkinter as tk
from tkinter import messagebox, ttk,filedialog
from core import SimpleFTPClient
import socket
import os

class FTPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Client FTP Simplifié")
        self.root.geometry("700x550")
        self.root.configure(bg="#1e1e2e")  # Fond global sombre

        self.client = None

        # --- STYLE / COULEURS ---
        self.bg_dark = "#1e1e2e"
        self.bg_card = "#252538"
        self.fg_white = "#cdd6f4"
        self.accent_blue = "#89b4fa"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"

        # Configuration des polices globales
        font_main = ("Helvetica", 10)
        font_bold = ("Helvetica", 10, "bold")

        # --- 1. BARRE DE CONNEXION ---
        conn_frame = tk.LabelFrame(root, text=" Connexion au Serveur ", bg=self.bg_card, fg=self.accent_blue, font=font_bold, bd=1, relief="solid", padx=10, pady=10)
        conn_frame.pack(fill="x", padx=15, pady=10)

        # Grille des éléments
        labels = ["Hôte:", "Port:", "User:", "Pass:"]
        self.entries = {}
        defaults = ["", "21", "", ""]
        shows = [None, None, None, "*"]

        for i, (label, default, show) in enumerate(zip(labels, defaults, shows)):
            lbl = tk.Label(conn_frame, text=label, bg=self.bg_card, fg=self.fg_white, font=font_main)
            lbl.grid(row=0, column=i*2, sticky="w", padx=2)
            
            ent = tk.Entry(conn_frame, bg="#11111b", fg=self.fg_white, insertbackground=self.fg_white, bd=1, relief="solid", font=font_main, width=10 if i!=1 else 5, show=show)
            ent.insert(0, default)
            ent.grid(row=0, column=i*2+1, padx=5, pady=5)
            self.entries[label] = ent

        self.btn_connect = tk.Button(conn_frame, text="Se connecter", command=self.connect_ftp, bg=self.accent_green, fg="#11111b", font=font_bold, bd=0, cursor="hand2", padx=10, pady=2)
        self.btn_connect.grid(row=0, column=8, padx=10)

        # --- 2. ZONE CENTRALE (LISTE DES FICHIERS) ---
        list_frame = tk.LabelFrame(root, text=" Explorateur de fichiers distants (Double-clic pour naviguer) ", bg=self.bg_card, fg=self.accent_blue, font=font_bold, bd=1, relief="solid", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # Utilisation de la Listbox avec un style sombre et une police Monospace propre
        self.file_listbox = tk.Listbox(list_frame, bg="#11111b", fg=self.fg_white, selectbackground=self.accent_blue, selectforeground="#11111b", bd=0, font=("Courier", 10), highlightthickness=0)
        self.file_listbox.pack(fill="both", expand=True, side="left")
        self.file_listbox.bind("<Double-Button-1>", self.on_double_click)

        # Scrollbar stylisée
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview, bg=self.bg_card)
        scrollbar.pack(fill="y", side="right")
        self.file_listbox.config(yscrollcommand=scrollbar.set)

        # --- 3. BARRE D'ACTIONS ---
        action_frame = tk.Frame(root, bg=self.bg_dark, pady=10)
        action_frame.pack(fill="x", padx=15)

       # Bouton Télécharger (Download)
        self.btn_download = tk.Button(action_frame, text="⬇ Télécharger le fichier sélectionné", command=self.download_selected, state=tk.DISABLED, bg=self.accent_blue, fg="#11111b", font=font_bold, bd=0, cursor="hand2", padx=15, pady=8)
        self.btn_download.pack(side="right")

        # Bouton Téléverser (Upload)
        self.btn_upload = tk.Button(action_frame, text="⬆ Téléverser un fichier", command=self.upload_action, state=tk.DISABLED, bg=self.accent_red, fg="#11111b", font=font_bold, bd=0, cursor="hand2", padx=15, pady=8)
        self.btn_upload.pack(side="right", padx=5)

    # --- MÉTHODES DE LOGIQUE (Identiques, adaptées pour le GUI) ---
    def connect_ftp(self):
        host = self.entries["Hôte:"].get()
        try:
            port = int(self.entries["Port:"].get())
        except ValueError:
            messagebox.showerror("Erreur", "Le port doit être un nombre.")
            return
            
        user = self.entries["User:"].get()
        password = self.entries["Pass:"].get()

        self.client = SimpleFTPClient(host=host, port=port)
        
        try:
            self.client.connect()
            if self.client.login(user, password):
                messagebox.showinfo("Succès", f"Connecté à {host}:{port} !")
                self.btn_download.config(state=tk.NORMAL, bg=self.accent_blue)
                self.btn_upload.config(state=tk.NORMAL)
                self.refresh_files()
            else:
                messagebox.showerror("Erreur", "Identifiants refusés.")
        except Exception as e:
            messagebox.showerror("Erreur de connexion", str(e))

    def refresh_files(self):
        self.file_listbox.delete(0, tk.END)
        self.file_listbox.insert(tk.END, "..")
        
        try:
            data_port = self.client._enter_passive_mode()
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_socket.connect((self.client.host, data_port))
            
            self.client._send_cmd("LIST")
            self.client._get_resp()
            
            listing = ""
            while True:
                data = data_socket.recv(4096)
                if not data:
                    break
                listing += data.decode('ascii')
            
            data_socket.close()
            self.client._get_resp()

            for line in listing.splitlines():
                if line.strip() and not line.endswith(" .") and not line.endswith(" .."):
                    self.file_listbox.insert(tk.END, line)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger la liste : {e}")

    def on_double_click(self, event):
        selection = self.file_listbox.curselection()
        if not selection:
            return

        index_selectionne = selection[0]
        selected_line = self.file_listbox.get(index_selectionne)
        
        # 1. Si c'est la toute première ligne de la liste, c'est FORCÉMENT le retour en arrière
        if index_selectionne == 0:
            filename = ".."
            is_directory = True
        else:
            # 2. Découpage pour les autres fichiers/dossiers (espaces inclus)
            parts = selected_line.split(None, 8)
            if len(parts) < 9:
                return
            filename = parts[-1]
            is_directory = selected_line.startswith('d')

        if is_directory:
            self.client._send_cmd(f"CWD {filename}")
            resp = self.client._get_resp()
            if "250" in resp:
                self.refresh_files()
            else:
                messagebox.showerror("Erreur", f"Impossible d'ouvrir : {filename}")

    def download_selected(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un fichier.")
            return

        selected_line = self.file_listbox.get(selection[0])
        
        if selected_line.startswith('d'):
            messagebox.showwarning("Type", "C'est un dossier ! Double-cliquez dessus pour l'ouvrir.")
            return
       
        parts = selected_line.split(None, 8)
        if len(parts) < 9:
        #parts = selected_line.split()
        #if not parts:
            return
        filename = parts[-1]
        
        # Cette fenêtre demande "Où voulez-vous enregistrer ce fichier ?"
        local_path = filedialog.asksaveasfilename(
            title=f"Enregistrer '{filename}' sous...",
            initialfile=filename,  # Propose le nom d'origine par défaut
            defaultextension=".*"  # Conserve l'extension d'origine
        )
        
        # Si l'utilisateur clique sur "Annuler", on arrête proprement
        if not local_path:
            return
        #success = self.client.download_file(filename, filename)
        success = self.client.download_file(filename, local_path)

        if success:
            messagebox.showinfo("Téléchargement", f"Fichier téléchargé avec succès !\nEmplacement : {local_path}")
            #messagebox.showinfo("Téléchargement", f"Fichier '{filename}' téléchargé !")
        else:
            messagebox.showerror("Téléchargement", "Le téléchargement a échoué.")
    
    def upload_action(self):
        """Ouvre un sélecteur de fichier local et téléverse le fichier choisi vers le serveur FTP."""
        
        # Ouvre la fenêtre de sélection de fichier sur l'OS
        file_path = filedialog.askopenfilename(title="Sélectionnez un fichier à envoyer au serveur")
        
        if not file_path:
            return  # L'utilisateur a annulé

        # Extraire uniquement le nom du fichier pour le serveur
        remote_name = os.path.basename(file_path)
        
        # Lancer l'upload via le core
        success = self.client.upload_file(file_path, remote_name)
        
        if success:
            messagebox.showinfo("Téléverser", f"Fichier '{remote_name}' envoyé avec succès !")
            self.refresh_files()  # Rafraîchir la liste pour voir apparaître le nouveau fichier !
        else:
            messagebox.showerror("Téléverser", "L'envoi du fichier a échoué.")

if __name__ == "__main__":
    root = tk.Tk()
    app = FTPClientGUI(root)
    root.mainloop()
