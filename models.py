from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
 

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(50), unique=True)
    firstname = db.Column(db.String(50))
    lastname = db.Column(db.String(50))
    mail = db.Column(db.String(255))
    password = db.Column(db.String(255))
    rank = db.Column(db.Integer)

    def serialize(self):
        return {
            'id':self.id,
            'firstname':self.firstname,
            'lastname':self.lastname,
            'mail':self.mail,
            'rank':self.rank,
            'password':"",
        }

class Dossier(db.Model):
    __tablename__='dossier'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    numero=db.Column(db.Integer)
    nom=db.Column(db.Text())
    id_groupe = db.Column(db.Integer)
    fullhash=db.Column(db.Text())
    id_owner = db.Column(db.Integer)
    url = db.Column(db.String(255))
    urlhtml = db.Column(db.String(255))
    urlhtmlcouleur = db.Column(db.String(255))
    type = db.Column(db.String(50))
    reservation = db.Column(db.Integer)

    def serialize(self):
        return {
            'id':self.id,
            'id_groupe':self.id_groupe,
            'numero':self.numero,
            'nom':self.nom,
            'fullhash':self.fullhash,
            'id_owner':self.id_owner,
            'url':self.url,
            'type':self.type,
            "reservation":self.reservation
        }

class Groupe(db.Model):
    __tablename__='groupe'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    nom = db.Column(db.String(50))

    def serialize(self):
        return {
            'id':self.id,
            'nom':self.nom
        }

class Resultat(db.Model):
    __tablename__='resultat'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    id_user = db.Column(db.Integer)
    id_dossier = db.Column(db.Integer)
    resultat = db.Column(db.Integer)
    motif = db.Column(db.String(250))

    def serialize(self):
        return {
            'id':self.id,
            'id_user':self.id_user,
            "id_dossier":self.id_dossier,
            'resultat':self.resultat,
            'motif':self.motif
        }

class ErreurDossier(db.Model):
    __tablename__='erreurdossier'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    id_user = db.Column(db.Integer)
    id_dossier = db.Column(db.Integer)
    motif = db.Column(db.String(250))

    def serialize(self):
        return {
            'id':self.id,
            'id_user':self.id_user,
            "id_dossier":self.id_dossier,
            'motif':self.motif
        }

class Permission(db.Model):
    __tablename__='permission'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    id_user = db.Column(db.Integer)
    id_groupe = db.Column(db.Integer)
    def serialize(self):
        return {
            'id':self.id,
            'id_user':self.id_user,
            'id_groupe':self.id_groupe
        }

class Preferences(db.Model):
    __tablename__='preference'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    id_user = db.Column(db.Integer)
    id_permission = db.Column(db.Integer)
    lecture = db.Column(db.Integer)
    def serialize(self):
        return {
            'id':self.id,
            'id_user':self.id_user,
            'id_permission':self.id_permission,
            'lecture':self.lecture
        }


class ConfigurationDetail(db.Model):
    __tablename__='configurationdetail'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_configuration=db.Column(db.Integer)
    lecture =db.Column(db.Integer)
    coloration = db.Column(db.Integer)
    pourcentageRelectureAcceptation = db.Column(db.Integer)
    pourcentageRelectureRefus = db.Column(db.Integer)
    def serialize(self):
        return {
        'id':self.id,
        'id_configuration':self.id_configuration,
        'lecture':self.lecture,
        "coloration":self.coloration,
        "pourcentageRelectureAcceptation":self.pourcentageRelectureAcceptation,
        "pourcentageRelectureRefus":self.pourcentageRelectureRefus
        }


class Configuration(db.Model):
    __tablename__='configuration'
    id = db.Column(db.Integer,primary_key=True, autoincrement=True)
    id_groupe = db.Column(db.Integer)
    phase1=db.Column(db.Integer)
    phase2=db.Column(db.Integer)
    phase3=db.Column(db.Integer)
    motsPositif=db.Column(db.Text())
    motsNegatif=db.Column(db.Text())
    feedbackAcceptation=db.Column(db.Integer)
    feedbackRefus=db.Column(db.Integer)



    def serialize(self):
        return {
            'id':self.id,
            'id_groupe':self.id_groupe,
            "phase1":self.phase1,
            'phase2':self.phase2,
            'phase3':self.phase3,
            'motsPositif':self.motsPositif,
            'motsNegatif':self.motsNegatif,
            "feedbackAcceptation":self.feedbackAcceptation,
            'feedbackRefus':self.feedbackRefus,

        }
