"# Espace Client - Application Bancaire (Démo style BNP)

Application web Flask reproduisant une interface bancaire moderne aux couleurs **blanc & vert** (inspiration BNP Paribas).

## Fonctionnalités

- Page de connexion sécurisée (démo)
- Tableau de bord avec 11 sections :
  - Accueil
  - Relevé
  - Bénéficiaires
  - Virement (avec envoi d'email de confirmation via **Resend**)
  - Prélèvements
  - Épargne
  - Crédits
  - Assurances
  - Services
  - Domiciliation
  - Messagerie

## Stack technique

- **Backend** : Flask (Python 3.10+)
- **Frontend** : Templates Jinja2 + HTML / CSS pur (aucun framework JS)
- **Email transactionnel** : [Resend](https://resend.com)

## Installation

```bash
# 1. Cloner / récupérer le projet
cd /app

# 2. Installer les dépendances
pip install -r requirements.txt
```

## Configuration

Créer (ou compléter) le fichier `.env` à la racine :

```env
RESEND_API_KEY=re_KMgWRn7H_H9j3PocFyfSQr931jJwg6gNH
SENDER_EMAIL=noreply@lre-certif.fr
FLASK_SECRET_KEY=changez-cette-cle-en-production
```

## Lancement

```bash
python app.py
```

L'application démarre sur : <http://localhost:5000>

## Identifiants de démonstration

| Champ        | Valeur     |
|--------------|------------|
| Identifiant  | `12345678` |
| Mot de passe | `demo1234` |

## Structure du projet

```
/app
├── app.py              # Application Flask (routes + données factices)
├── requirements.txt    # Dépendances Python
├── .env                # Variables d'environnement (clés API)
├── README.md           # Ce fichier
└── templates/
    ├── login.html      # Page de connexion
    └── dash.html       # Tableau de bord (toutes sections)
```

## Routes principales

| Méthode | Route        | Description                                       |
|---------|--------------|---------------------------------------------------|
| GET     | `/`          | Redirige vers `/login` ou `/dashboard`            |
| GET/POST| `/login`     | Page de connexion                                  |
| GET     | `/dashboard` | Tableau de bord (param `?section=...`)            |
| POST    | `/virement`  | Création d'un virement + email de confirmation    |
| GET     | `/logout`    | Déconnexion                                        |

## Personnalisation

- **Couleurs** : modifier les variables CSS dans `templates/dash.html` et `templates/login.html` (variables `--brand-green`, etc.)
- **Données** : éditer les listes Python (`COMPTES`, `OPERATIONS`, `BENEFICIAIRES`, etc.) dans `app.py`

## Notes importantes

- L'authentification est **factice** (à des fins de démonstration uniquement).
- Les données affichées sont **fictives** et stockées en mémoire.
- En mode test Resend, les emails ne sont délivrés qu'aux adresses vérifiées.

## Licence

Projet de démonstration — usage interne.
"