"""Smart IT Assistant — outil pédagogique de diagnostic Windows.

Dépendance : pip install psutil
Lancement : python smart_it_assistant_pro.py
"""
from __future__ import annotations

import datetime as dt
import os
import platform
import socket
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import psutil

APP_NAME = "Smart IT Assistant"
VERSION = "2.0"
BG = "#F0F4F8"
WHITE = "#FFFFFF"
NAVY = "#1E3A5F"
TEXT = "#263238"
MUTED = "#64748B"
GREEN = "#167347"
AMBER = "#A66300"
RED = "#B42318"
BORDER = "#DCE5EF"


def go(value: float) -> float:
    """Convertit des octets en gigaoctets, arrondis à 1 décimale."""
    return round(value / (1024 ** 3), 1)



def recueillir_diagnostic() -> dict:
    """Lit des métriques système sans modifier la configuration du PC."""
    memoire = psutil.virtual_memory()
    disque_racine = Path.home().anchor or os.path.abspath(os.sep)
    disque = psutil.disk_usage(disque_racine)
    cpu = psutil.cpu_percent(interval=0.5)
    ram_alerte = memoire.percent >= 80
    disque_alerte = disque.percent >= 85
    cpu_alerte = cpu >= 85
    return {
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "nom_pc": platform.node() or "Inconnu",
        "systeme": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu_logiques": psutil.cpu_count(logical=True),
        "cpu_physiques": psutil.cpu_count(logical=False),
        "cpu_pourcent": cpu,
        "ram_totale_go": go(memoire.total),
        "ram_disponible_go": go(memoire.available),
        "ram_pourcent": memoire.percent,
        "disque": disque_racine,
        "disque_total_go": go(disque.total),
        "disque_libre_go": go(disque.free),
        "disque_pourcent": disque.percent,
        "alertes": {"cpu": cpu_alerte, "ram": ram_alerte, "disque": disque_alerte},
    }


def tester_reseau() -> dict:
    """Teste une connexion TCP externe : ce n'est PAS un test de débit Internet."""
    cible, port = "1.1.1.1", 443
    debut = dt.datetime.now().astimezone()
    try:
        with socket.create_connection((cible, port), timeout=3):
            pass
        return {
            "date": debut.isoformat(timespec="seconds"),
            "succes": True,
            "detail": f"Connexion TCP vers {cible}:{port} réussie.",
            "limite": "Le test vérifie l'accès à cette cible, pas la vitesse ni tous les sites.",
        }
    except OSError as erreur:
        return {
            "date": debut.isoformat(timespec="seconds"),
            "succes": False,
            "detail": f"Connexion TCP vers {cible}:{port} impossible : {erreur}",
            "limite": "Cela ne prouve pas à lui seul une panne générale d'Internet.",
        }


class SmartITAssistant(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} | Diagnostic")
        self.geometry("900x760")
        self.minsize(700, 610)
        self.configure(bg=BG)
        self.diagnostic: dict | None = None
        self.reseau: dict | None = None
        self.en_cours = False
        self._construire_interface()

    def _texte(self, parent, contenu, taille=11, couleur=TEXT, gras=False, fond=WHITE, **options):
        return tk.Label(
            parent, text=contenu, font=("Segoe UI", taille, "bold" if gras else "normal"),
            fg=couleur, bg=fond, **options
        )

    def _carte(self, parent):
        cadre = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        cadre.pack(fill="x", pady=(0, 14))
        return cadre

    def _ligne(self, parent, titre, valeur):
        ligne = tk.Frame(parent, bg=WHITE)
        ligne.pack(fill="x", pady=4)
        self._texte(ligne, titre, couleur=MUTED, anchor="w").pack(side="left")
        self._texte(ligne, str(valeur), gras=True, anchor="e").pack(side="right")

    def _separateur(self, parent):
        tk.Frame(parent, height=1, bg=BORDER).pack(fill="x", pady=11)

    def _construire_interface(self):
        # Un Canvas avec barre de défilement évite de couper les résultats sur petit écran.
        conteneur = tk.Frame(self, bg=BG)
        conteneur.pack(fill="both", expand=True)
        canvas = tk.Canvas(conteneur, bg=BG, highlightthickness=0)
        barre = ttk.Scrollbar(conteneur, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.corps = tk.Frame(canvas, bg=BG)
        self.fenetre_canvas = canvas.create_window((0, 0), window=self.corps, anchor="nw")
        self.corps.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(self.fenetre_canvas, width=e.width))

        contenu = tk.Frame(self.corps, bg=BG)
        contenu.pack(fill="both", expand=True, padx=32, pady=24)
        self._texte(contenu, APP_NAME, 22, NAVY, True, BG).pack(anchor="center")
        self._texte(contenu, "Tableau de bord de diagnostic • Lecture seule", 10, MUTED, fond=BG).pack(pady=(4, 22))

        # Carte 1 : métriques matérielles et système.
        carte_pc = self._carte(contenu)
        zone_pc = tk.Frame(carte_pc, bg=WHITE)
        zone_pc.pack(fill="x", padx=24, pady=20)
        self._texte(zone_pc, "▣  Diagnostic de l'ordinateur", 14, NAVY, True).pack(anchor="w")
        self._separateur(zone_pc)
        self.zone_infos = tk.Frame(zone_pc, bg=WHITE)
        self.zone_infos.pack(fill="x")
        self._texte(self.zone_infos, "Clique sur « Actualiser le diagnostic » pour analyser ce PC.",
                    couleur=MUTED, anchor="w", justify="left", wraplength=650).pack(anchor="w", pady=8)
        self._separateur(zone_pc)
        self.zone_alertes = tk.Frame(zone_pc, bg=WHITE)
        self.zone_alertes.pack(fill="x")
        self._texte(self.zone_alertes, "○  Aucun diagnostic effectué", couleur=MUTED).pack(anchor="w")

        # Carte 2 : test réseau séparé, avec explication honnête du test.
        carte_reseau = self._carte(contenu)
        zone_reseau = tk.Frame(carte_reseau, bg=WHITE)
        zone_reseau.pack(fill="x", padx=24, pady=18)
        self._texte(zone_reseau, "◉  Vérification de la connexion réseau", 13, NAVY, True).pack(anchor="w")
        self.reseau_etat = self._texte(zone_reseau, "○  Test non effectué", 11, MUTED, fond=WHITE, anchor="w")
        self.reseau_etat.pack(fill="x", pady=(10, 3))
        self.reseau_detail = self._texte(zone_reseau, "Test TCP vers 1.1.1.1:443 (ce n'est pas un test de débit).",
                                         9, MUTED, fond=WHITE, anchor="w", justify="left", wraplength=680)
        self.reseau_detail.pack(fill="x")

        # Boutons : mêmes largeurs, espaces réguliers et désactivation durant les tests.
        commandes = tk.Frame(contenu, bg=BG)
        commandes.pack(fill="x", pady=(2, 10))
        for colonne in range(3):
            commandes.columnconfigure(colonne, weight=1, uniform="boutons")
        self.btn_pc = self._bouton(commandes, "Actualiser le diagnostic", self.lancer_diagnostic, NAVY, 0)
        self.btn_reseau = self._bouton(commandes, "Tester la connexion", self.lancer_reseau, NAVY, 1)
        self.btn_rapport = self._bouton(commandes, "Enregistrer un rapport", self.enregistrer_rapport, GREEN, 2)
        self.etat = self._texte(contenu, "Prêt. Aucun changement n'est effectué sur le PC.",
                                9, MUTED, fond=BG)
        self.etat.pack(anchor="w", pady=(5, 0))
        self._texte(contenu, f"Version {VERSION}  •  Python / Tkinter / psutil  •  Outil de premier niveau",
                    9, MUTED, fond=BG).pack(anchor="center", pady=(18, 0))

    def _bouton(self, parent, titre, commande, couleur, colonne):
        bouton = tk.Button(parent, text=titre, command=commande, bg=couleur, fg="white",
                           activebackground="#315C88" if couleur == NAVY else "#218451",
                           activeforeground="white", font=("Segoe UI", 10, "bold"),
                           relief="flat", cursor="hand2", padx=12, pady=12)
        bouton.grid(row=0, column=colonne, padx=5, sticky="ew")
        return bouton

    def _vider(self, parent):
        for enfant in parent.winfo_children():
            enfant.destroy()

    def _alerte(self, parent, titre, probleme, recommandation):
        couleur = RED if probleme else GREEN
        symbole = "⚠" if probleme else "✓"
        self._texte(parent, f"{symbole}  {titre}", 10, couleur, True,
                    anchor="w", justify="left").pack(fill="x", pady=(4, 1))
        if probleme:
            self._texte(parent, f"     Conseil : {recommandation}", 9, MUTED,
                        anchor="w", justify="left", wraplength=650).pack(fill="x", pady=(0, 5))

    def _travail(self, fonction, callback, message):
        if self.en_cours:
            return
        self.en_cours = True
        self.btn_pc.configure(state="disabled")
        self.btn_reseau.configure(state="disabled")
        self.etat.configure(text=message)

        def tache():
            try:
                resultat = fonction()
                self.after(0, lambda: terminer(resultat, None))
            except Exception as erreur:
                self.after(0, lambda msg=str(erreur): terminer(None, msg))

        def terminer(resultat, erreur):
            self.en_cours = False
            self.btn_pc.configure(state="normal")
            self.btn_reseau.configure(state="normal")
            if erreur:
                self.etat.configure(text="Une erreur s'est produite.")
                messagebox.showerror("Erreur de diagnostic", erreur)
            else:
                callback(resultat)
                self.etat.configure(text=f"Dernière opération : {dt.datetime.now():%d/%m/%Y %H:%M:%S}")

        threading.Thread(target=tache, daemon=True).start()

    def lancer_diagnostic(self):
        self._travail(recueillir_diagnostic, self.afficher_diagnostic, "Analyse du PC en cours…")

    def afficher_diagnostic(self, donnees):
        self.diagnostic = donnees
        self._vider(self.zone_infos)
        valeurs = [
            ("Nom du PC", donnees["nom_pc"]),
            ("Système d'exploitation", donnees["systeme"]),
            ("Architecture", donnees["architecture"]),
            ("Processeurs logiques", donnees["cpu_logiques"]),
            ("Processeurs physiques", donnees["cpu_physiques"] or "Non disponible"),
            ("CPU utilisé (mesure ponctuelle)", f'{donnees["cpu_pourcent"]:.1f} %'),
            ("RAM totale", f'{donnees["ram_totale_go"]:.1f} Go'),
            ("RAM disponible", f'{donnees["ram_disponible_go"]:.1f} Go'),
            ("RAM utilisée", f'{donnees["ram_pourcent"]:.1f} %'),
            (f'Disque {donnees["disque"]} — capacité', f'{donnees["disque_total_go"]:.1f} Go'),
            ("Disque libre", f'{donnees["disque_libre_go"]:.1f} Go'),
            ("Disque utilisé", f'{donnees["disque_pourcent"]:.1f} %'),
        ]
        for nom, valeur in valeurs:
            self._ligne(self.zone_infos, nom, valeur)
        self._vider(self.zone_alertes)
        alertes = donnees["alertes"]
        self._alerte(self.zone_alertes, "CPU : utilisation élevée" if alertes["cpu"] else "CPU : utilisation normale",
                     alertes["cpu"], "Fermer les tâches inutiles et consulter le Gestionnaire des tâches.")
        self._alerte(self.zone_alertes, "RAM : utilisation élevée" if alertes["ram"] else "RAM : utilisation normale",
                     alertes["ram"], "Fermer des applications et examiner leur consommation mémoire.")
        self._alerte(self.zone_alertes, "Disque : espace faible" if alertes["disque"] else "Disque : espace suffisant",
                     alertes["disque"], "Vérifier les fichiers volumineux et utiliser Nettoyage de disque après validation.")

    def lancer_reseau(self):
        self.reseau_etat.configure(text="◌  Test réseau en cours…", fg=MUTED)
        self._travail(tester_reseau, self.afficher_reseau, "Test de connexion en cours (3 secondes maximum)…")

    def afficher_reseau(self, donnees):
        self.reseau = donnees
        reussi = donnees["succes"]
        self.reseau_etat.configure(text="✓  Connexion à la cible réussie" if reussi else "⚠  Connexion à la cible impossible",
                                  fg=GREEN if reussi else RED)
        self.reseau_detail.configure(text=donnees["detail"] + "\n" + donnees["limite"])

    def _rapport_texte(self):
        lignes = [f"{APP_NAME} — RAPPORT DE DIAGNOSTIC", f"Version : {VERSION}",
                  f"Rapport généré : {dt.datetime.now().astimezone():%d/%m/%Y %H:%M:%S %Z}", ""]
        if self.diagnostic:
            d = self.diagnostic
            lignes += ["=== DIAGNOSTIC DU PC ===", f"Date de mesure : {d['date']}",
                       f"Nom : {d['nom_pc']}", f"Système : {d['systeme']}",
                       f"Architecture : {d['architecture']}",
                       f"CPU logiques : {d['cpu_logiques']}", f"CPU physiques : {d['cpu_physiques']}",
                       f"CPU utilisé : {d['cpu_pourcent']:.1f} %",
                       f"RAM totale : {d['ram_totale_go']:.1f} Go",
                       f"RAM disponible : {d['ram_disponible_go']:.1f} Go",
                       f"RAM utilisée : {d['ram_pourcent']:.1f} %",
                       f"Disque : {d['disque']}", f"Disque total : {d['disque_total_go']:.1f} Go",
                       f"Disque libre : {d['disque_libre_go']:.1f} Go",
                       f"Disque utilisé : {d['disque_pourcent']:.1f} %", "",
                       "=== ALERTES ET CONSEILS ==="]
            conseils = {
                "cpu": "Examiner les processus dans le Gestionnaire des tâches.",
                "ram": "Examiner les applications gourmandes en mémoire.",
                "disque": "Vérifier les fichiers volumineux et nettoyer après validation.",
            }
            for cle, nom in [("cpu", "CPU"), ("ram", "RAM"), ("disque", "Disque")]:
                alerte = d["alertes"][cle]
                lignes.append(f"{nom} : {'À vérifier — ' + conseils[cle] if alerte else 'Normal'}")
        else:
            lignes.append("Diagnostic PC non effectué.")
        lignes += ["", "=== TEST RÉSEAU ==="]
        if self.reseau:
            lignes += [f"Date du test : {self.reseau['date']}", self.reseau["detail"], self.reseau["limite"]]
        else:
            lignes.append("Test réseau non effectué.")
        lignes += ["", "Note : diagnostic indicatif, non exhaustif. Les mesures sont ponctuelles."]
        return "\n".join(lignes) + "\n"

    def enregistrer_rapport(self):
        if not self.diagnostic and not self.reseau:
            messagebox.showwarning("Rapport vide", "Effectue au moins un diagnostic ou un test réseau avant l'export.")
            return
        chemin = filedialog.asksaveasfilename(
            title="Enregistrer le rapport", defaultextension=".txt",
            initialfile=f"diagnostic_{dt.datetime.now():%Y%m%d_%H%M}.txt",
            filetypes=[("Rapport texte", "*.txt")]
        )
        if not chemin:
            return
        try:
            with open(chemin, "w", encoding="utf-8") as fichier:
                fichier.write(self._rapport_texte())
        except OSError as erreur:
            messagebox.showerror("Enregistrement impossible", str(erreur))
        else:
            messagebox.showinfo("Rapport enregistré", f"Rapport créé :\n{chemin}")


if __name__ == "__main__":
    application = SmartITAssistant()
    application.mainloop()
