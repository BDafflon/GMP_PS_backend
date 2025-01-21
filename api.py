


import os
import re
import shutil
import subprocess
from os.path import join

from flask import Flask, render_template, request, jsonify, make_response, send_file
from flask_migrate import Migrate
from sqlalchemy import func
from sqlalchemy.orm import session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import random
import string
import hashlib
import json

import os


from id import getid
from models import db, User, Dossier, Groupe, Resultat,Permission,Configuration,ConfigurationDetail,Preferences

from engineio.payload import Payload




app = Flask(__name__)
app.config['CORS_HEADERS'] = '*'

CORS(app, origins="*", allow_headers="*")
app.config['SECRET_KEY'] = 'thisissecret'
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://"+getid()[0]+":"+getid()[1]+"@localhost:5432/parcoursup"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['CORS_HEADERS'] = 'Content-Type'

ALLOWED_EXTENSIONS = {'txt', 'doc', 'dox', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'zip', 'rar', 'csv'}

db.init_app(app)
migrate = Migrate(app, db)

liveUser = {}


@app.route('/')
def home():
    return "[/configuration pour une premiere utilisation]"

#----------------------------------------- SECURITY ------------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        #print("Valide Token")

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        #print("token ",token)
        if not token:
            #print('Token is missing! ',request.headers)
            return jsonify({'message' : 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],algorithms=["HS256"])
            #print(data)
            current_user = User.query.filter_by(id=data['id']).first()
        except  Exception as exc:
            #print(exc)
            return jsonify({'message' : 'Token is invalid!'}), 401

        if current_user is None:
            return jsonify({'message': 'User is invalid!'}), 401
        return f(current_user, *args, **kwargs)

    return decorated




@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response(f"Could not verify {auth.username}", 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    user = User.query.filter_by(mail=auth.username).first()

    if not user:
        return make_response(f"Could not verify {auth.username}", 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})

    if check_password_hash(user.password, auth.password):
        if user.rank==0:
            elapseTime=3000
        else:
            elapseTime = 3000
        token = jwt.encode({'id' : user.id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=elapseTime)}, app.config['SECRET_KEY'],algorithm="HS256")

        print("log",token,user.rank)
        try:
            token = token.decode()
        except:
            print("error decode")
        return jsonify({'token' : token, 'rank':user.rank, 'id':user.id})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'})


#------------------------ Preference

@app.route('/preference/update', methods = ['POST'])
@token_required
def updatePref(current_user):
    #print("UPDATE PREF",request.json)
    preference = Preferences.query.filter_by(id=request.json["pref"],id_user=request.json["id"]).first()
    if preference is not None:
        preference.lecture = request.json["lecture"]
        db.session.commit()

        reservation = Dossier.query.filter_by(reservation=request.json["id"]).all()
        for r in reservation:
            r.reservation = 0
            db.session.commit()

        return jsonify(preference.serialize())
    return jsonify({})



#------------------------ Permission


@app.route('/permission/groupe/<int:id>', methods = ['GET'])
@token_required
def get_perm_by_group(current_user,id):
    if current_user.rank!=0:
        return jsonify([])

    perm = Permission.query.filter_by(id_groupe=id).all()
    data=[]
    for p in perm:
        data.append(p.serialize())

    return jsonify(data)


@app.route('/permission/update', methods = ['POST'])
@token_required
def update_perm(current_user):
    if current_user.rank!=0:
        return jsonify([])

    print("permission",request.json)
    permission = Permission.query.filter_by(id_user=request.json["user"]).all()
    for p in permission:
        db.session.delete(p)

    preference = Preferences.query.filter_by(id_user=request.json["user"]).all()
    for p in preference:
        db.session.delete(p)

    reservation = Dossier.query.filter(Dossier.reservation != 0).all()
    for r in reservation:
        r.reservation=0

    db.session.commit()

    for p in request.json["permission"]:
        perm = Permission(id_user=request.json["user"])
        perm.id_groupe = p
        db.session.add(perm)
        db.session.commit()

        pref = Preferences(id_user=request.json["user"])
        pref.id_permission=perm.id
        pref.lecture=1
        db.session.add(pref)
        db.session.commit()

    db.session.commit()
    user = User.query.filter_by(id=request.json["user"]).first()
    return jsonify(user.serialize())

@app.route('/permission/registration', methods=['POST'])
@token_required
def registration_perm(current_user):
    if current_user.rank != 0:
        return jsonify([])

    #print("permission", request.json)
    p = Permission(id_user=request.json["user"]["id"])
    p.id_groupe = request.json["groupe"]

    db.session.add(p)
    db.session.commit()

    return jsonify(p.serialize())



#------------------------ USER
@app.route('/user/trash/<int:id>', methods=['DELETE'])
@token_required
def del_user(current_user,id):
    #print("del",current_user)
    if current_user.rank != 0:
        return make_response('Could not verify', 405, {'WWW-Authenticate': 'Basic realm="Admin required!"'})

    if id!=current_user.id:
        user=User.query.filter_by(id=id).delete()
    print(user)
    db.session.commit()

    return jsonify({"id":id})


@app.route('/users/relectures/<int:id>', methods=['GET'])
@token_required
def get_relectures_by_user(current_user,id):
    #print("del",current_user)
    if current_user.rank != 0:
        return make_response('Could not verify', 405, {'WWW-Authenticate': 'Basic realm="Admin required!"'})


    resultats=Resultat.query.filter_by(id=id).all()
    data=[]
    for r in resultats:
        data.append(r.serialize())

    #print(data)


    return jsonify(data)



@app.route('/user/<int:id>', methods = ['GET'])
@token_required
def get_user(current_user,id):
    u = User.query.filter_by(id=id).first()
    if u is not None:
        us = u.serialize()
        us["permission"] = []
        us["relecture"] = []


        resultats = Resultat.query.filter_by(id=u.id).all()
        for r in resultats:
            us["relecture"].append(r.serialize())



        permissions = Permission.query.filter_by(id_user=u.id).all()
        for p in permissions:
            nomGroupe = Groupe.query.filter_by(id=p.id_groupe).first()
            pref = Preferences.query.filter_by(id_user=u.id,id_permission=p.id).first()
            if nomGroupe is not None:
                gs = nomGroupe.serialize()
                if pref is not None:
                    gs["preference"]=pref.serialize()
                us["permission"].append(gs)

        return jsonify(us)
    return jsonify([])

@app.route('/users', methods = ['GET'])
@token_required
def get_users(current_user):
    if current_user.rank!=0:
        return jsonify([])

    users = User.query.all()
    data=[]
    for u in users:
        us = u.serialize()
        us["permission"]=[]
        us["relecture"] = []

        resultats = Resultat.query.filter_by(id_user=u.id).all()
        for r in resultats:
            us["relecture"].append(r.serialize())


        permissions = Permission.query.filter_by(id_user=u.id).all()
        for p in permissions:
            nomGroupe=Groupe.query.filter_by(id=p.id_groupe).first()
            if nomGroupe is not None:
                us["permission"].append(nomGroupe.serialize())

        data.append(us)

    return jsonify(data)


@app.route('/user/update', methods = ['POST'])
@token_required
def update_user(current_user):
    if current_user.rank!=0:
        return jsonify([])

    user = User.query.filter_by(id=request.json["id"]).first()
    if user is not None:
        if request.json["type"]=="rank":
            user.rank=request.json["value"]
        if request.json["type"]=="pwd":
            user.password = generate_password_hash(request.json["value"])


    db.session.commit()
    return jsonify(user.serialize())


@app.route('/user/registration', methods = ['POST'])
@token_required
def registration_user(current_user):
    if current_user.rank!=0:
        return jsonify([])

    #print("reg user",request.json)
    u=User(lastname=request.json["user"][0])
    u.firstname=request.json["user"][1]
    u.mail=request.json["user"][3]
    u.password = generate_password_hash(request.json["user"][2])
    u.rank=1
    db.session.add(u)
    db.session.commit()

    return jsonify(u.serialize())

#------------------------ DOSSIER
@app.route('/dossier/lecture/test', methods = ['GET'])
def getDossierLecturetest():
    dossier = Dossier.query.first()
    return send_file(dossier.url, mimetype=dossier.type, as_attachment=True)


def getdossier2(current_user,force,id=None):
    #print("----------SELECTION DOSSIER--------------")
    if current_user.rank == 0 and id is not None:
        dossier=Dossier.query.filter_by(id=id).first()
        if dossier is  not None:
            return send_file(dossier.urlhtmlcouleur, mimetype="text/html", as_attachment=True)
        else:
            return

    dossier = Dossier.query.filter_by(reservation=current_user.id).first()
    if force == 1 and dossier is not None:
        dossier.reservation=0
        db.session.commit()
        dossier=None

    if dossier is not None:
        return send_file(dossier.urlhtmlcouleur, mimetype="text/html", as_attachment=True)

    sql='''SELECT dossier.id,dossier.id_groupe,count(dossier.id),sum(resultat)
    FROM dossier,resultat 
    WHERE dossier.id=resultat.id_dossier 
    GROUP BY dossier.id,dossier.id_groupe
    
    union
    
    SELECT dossier.id,dossier.id_groupe,0,0
    FROM dossier
    WHERE dossier.id not in (
    SELECT dossier.id
    FROM dossier,resultat 
    WHERE dossier.id=resultat.id_dossier 
    GROUP BY dossier.id
    )'''
    res = db.session.execute(sql)

    dossier=[]
    confDict={}
    conf = Configuration.query.all()
    for c in conf:
        if c.id_groupe not in confDict.keys():
            c1 = ConfigurationDetail.query.filter_by(id=c.phase1).first()
            c2 = ConfigurationDetail.query.filter_by(id=c.phase2).first()
            c3 = ConfigurationDetail.query.filter_by(id=c.phase3).first()
            sub_conf={}
            if c1 is not None:
                sub_conf[0]=c1.serialize()
            if c2 is not None:
                sub_conf[1]=c2.serialize()
            if c3 is not None:
                sub_conf[2]=c3.serialize()
            confDict[c.id_groupe]=sub_conf

    sql2='''SELECT id_groupe
    FROM permission, preference
    WHERE permission.id=preference.id_permission
    and lecture=1
    and preference.id_user='''+str(current_user.id)
    permission = db.session.execute(sql2)
    permissionList=[i[0] for i in permission]
    dejalu = [i.id_dossier for i in Resultat.query.filter_by(id_user=current_user.id).all()]
    #print("permissionList",permissionList)
    #print("confDict",confDict)
    #print("dejalu ",current_user.id,":",dejalu)


    for row in res:
        if row[0] not in dejalu:
            if row[1] in permissionList:
                if row[2]==0 and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])

                if row[2]==1 and row[3]==1 and 0 < random.randint(0,100) < confDict[row[1]][row[2]]["pourcentageRelectureAcceptation"] and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])
                if row[2]==1 and row[3]==-1 and 0 < random.randint(0,100) < confDict[row[1]][row[2]]["pourcentageRelectureRefus"] and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])

                if current_user.rank==0 and row[2]==2 and row[3]>0 and 0 < random.randint(0,100) < confDict[row[1]][row[2]]["pourcentageRelectureAcceptation"] and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])
                if current_user.rank==0 and row[2]==2 and row[3]<0 and 0 < random.randint(0,100) < confDict[row[1]][row[2]]["pourcentageRelectureRefus"] and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])
                if current_user.rank==0 and row[2]==2 and row[3]==0 and confDict[row[1]][row[2]]["lecture"]==1:
                    dossier.append(row[0])


    #print("dossier",dossier)
    if len(dossier)==0:
        return  send_file("./placeholder.html", mimetype="text/html", as_attachment=True)
    x = random.randint(0, len(dossier) - 1)
    d = Dossier.query.filter_by(id=dossier[x]).first()
    d.reservation = current_user.id
    db.session.commit()
    return send_file(d.urlhtmlcouleur, mimetype="text/html", as_attachment=True)



def getdossier(current_user,force,id=None):
    if current_user.rank == 0 and id is not None:
        dossier=Dossier.query.filter_by(id=id).first()
        if dossier is  not None:
            return send_file(dossier.urlhtmlcouleur, mimetype="text/html", as_attachment=True)
        else:
            return

    dossier = Dossier.query.filter_by(reservation=current_user.id).first()
    if force == 1 and dossier is not None:
        dossier.reservation=0
        db.session.commit()
        dossier=None

    if dossier is not None:
        return send_file(dossier.urlhtmlcouleur, mimetype="text/html", as_attachment=True)

    pref = Preferences.query.filter_by(id_user=current_user.id,lecture=1 ).all()
    dossier1 = []
    dossier2 = []
    dossier3 = []

    for p in pref:
        #print("dossier ? pref", p)
        permission = Permission.query.filter_by(id=p.id_permission).first()
        if permission is not None:
            #print("dossier ? permission", permission.id_groupe)
            dossiers = Dossier.query.filter_by(id_groupe=permission.id_groupe,reservation=0).all()
            for d in dossiers:
                phase = len(Resultat.query.filter_by(id_dossier=d.id).all())+1
                #print("dossier ?",d,phase)
                conf = Configuration.query.filter_by(id_groupe=permission.id_groupe).first()
                c1 = ConfigurationDetail.query.filter_by(id=conf.phase1).first()
                c2 = ConfigurationDetail.query.filter_by(id=conf.phase2).first()
                c3 = ConfigurationDetail.query.filter_by(id=conf.phase3).first()


                if phase==1 and c1.lecture==1:
                    dossier1.append((d))
                if phase==2 and c2.lecture==1:
                    dejalu=Resultat.query.filter_by(id_dossier=d.id,id_user=current_user.id).first()
                    x = random.randint(0,100)
                    if dejalu.id_user!=current_user.id:
                        if dejalu.resultat==-1 and x<c2.pourcentageRelectureRefus or dejalu.resultat==1 and x<c2.pourcentageRelectureAcceptation :
                            dossier2.append((d))
                if phase==3 and c3.lecture==1:
                    dejalu = Resultat.query.filter_by(id_dossier=d.id, id_user=current_user.id).all()
                    if dejalu[0].resultat * dejalu[1].resultat<0:
                        dossier3.append((d))
                    else:
                        if dejalu[0].resultat == -1 and x < c3.pourcentageRelectureRefus or dejalu[0].resultat == 1 and x < c3.pourcentageRelectureAcceptation:
                            dossier3.append((d))

    dossierList = dossier1+dossier2+dossier3
    #print("Get Dossier ",dossierList)
    if len(dossierList)==0:
        return  send_file("./placeholder.html", mimetype="text/html", as_attachment=True)
    x = random.randint(0,len(dossierList)-1)
    #print("dossier",x)
    dossierList[x].reservation=current_user.id
    db.session.commit()

    return send_file(dossierList[x].urlhtmlcouleur, mimetype="text/html", as_attachment=True)





@app.route('/dossier/lecture/<int:force>', methods = ['GET'])
@token_required
def getDossierLecture(current_user,force):
    return getdossier2(current_user,force)

@app.route('/dossier', methods = ['POST'])
@token_required
def getDossier(current_user):
    return getdossier2(current_user,0,request.json["dossier"]['id'])





@app.route('/dossier/groupe/<int:id>', methods = ['GET'])
@token_required
def get_dossier_by_group(current_user,id):
    if current_user.rank!=0:
        return jsonify([])

    dossier = Dossier.query.filter_by(id_groupe=id).all()
    data=[]
    for p in dossier:
        data.append(p.serialize())

    return jsonify(data)


def processColoration(path,dest):
    print(path)
    print(dest)
    configuration = Configuration.query.first()
    css = r'''<style type="text/css">
        .neg-5{background: rgb(255, 0, 0)}
        .neg-4{background: rgb(255, 60, 60)}
        .neg-3{background: rgb(255, 120, 120)}
        .neg-2{background: rgb(255, 180, 180)}
        .neg-1{background: rgb(255, 220, 220)}
        .pos-5{background: rgb(0, 255, 0)}
        .pos-4{background: rgb(60, 255, 60)}
        .pos-3{background: rgb(120, 255, 120)}
        .pos-2{background: rgb(180, 255, 180)}
        .pos-1{background: rgb(220, 255, 220)}
        '''

    print("Coloration ", path)
    file = open(path, mode='r', encoding="utf8")
    doc = file.read()

    doc= doc.replace('visibility:hidden;',"").replace('"pc','"')
    content = doc.split('<body>')[1]

    head = doc.split('<body>')[0]
    head = re.sub(r'<style type="text/css">', css, head, 1)

    apreciation = content.split('ciations des professeurs :')
    if len(apreciation) > 1:
        buletin = content.split('ciations des professeurs :')[0]
        lettre = 'ciations des professeurs :' + 'ciations des professeurs :'.join(
            content.split('ciations des professeurs :')[1:])
    else:
        buletin = content.split('Projet de formation motiv')[0]
        lettre = 'Projet de formation motiv' + 'Projet de formation motiv'.join(
            content.split('Projet de formation motiv')[1:])

    buletin = buletin.replace("&apos;", "'")


    if configuration is not None:
        pos = configuration.motsPositif.split("\n")
        neg = configuration.motsNegatif.split("\n")

        for n in neg:
            if n == "":
                continue
            find = re.findall(r"\b" + n + r"\b", buletin, flags=re.IGNORECASE)
            for fi in find:
                match = re.subn(r'\b' + fi + r'\b', '<span class="neg-5">' + fi + '</span>', buletin,
                                flags=re.IGNORECASE)
                buletin = match[0]


        for n in pos:
            if n=="":
                continue
            find = re.findall(r"\b" + n + r"\b", buletin, flags=re.IGNORECASE)
            for fi in find:
                match = re.subn(r'\b' + fi + r'\b', '<span class="pos-5">' + fi + '</span>', buletin,
                                flags=re.IGNORECASE)
                buletin = match[0]


        file.close()
        file = open(dest, mode='w', encoding="utf8")
        data = head + '<body>' + buletin + lettre
        file.write(data)
        file.close()
        return dest



    return 0

@app.route('/uploader', methods = ['GET', 'POST'])
@token_required
def upload_file(current_user):
    if request.method == 'POST':
        f = request.files['file']
        g = request.form.get('groupe')
        print("UPLOAD FILE -----------------------")
        print(g)


        letters = string.ascii_lowercase
        pathPDF= '2023/pdf/'
        pathHTML = '2023/html/'
        pathHTMLCouleur = '2023/htmlcouleur/'
        os.makedirs(os.path.dirname("./tmp/"+pathPDF), exist_ok=True)



        print('--save file',pathPDF+secure_filename(f.filename))
        f.save("./tmp/"+pathPDF+secure_filename(f.filename))


        BLOCKSIZE = 65536
        hasher = hashlib.sha1()
        with open("./tmp/"+pathPDF+secure_filename(f.filename), 'rb') as tmp:
            buf = tmp.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = tmp.read(BLOCKSIZE)

        hash = hasher.hexdigest()
        dossier = Dossier.query.filter_by(fullhash=hash, id_owner=current_user.id).first()
        if dossier is not None:
            return jsonify({'path': "/media/" + str(dossier.id), 'type': dossier.type})
        print("-- Copie pdf")
        os.makedirs(os.path.dirname("./media/"+ pathPDF  + secure_filename(f.filename)),exist_ok=True)
        shutil.copy2("./tmp/"+pathPDF+secure_filename(f.filename),"./media/"+pathPDF+secure_filename(f.filename))

        os.makedirs(os.path.dirname("./media/" + pathHTML), exist_ok=True)
        os.makedirs(os.path.dirname("./media/" + pathHTMLCouleur), exist_ok=True)
        shutil.copy2("./tmp/" + pathPDF + secure_filename(f.filename),"./media/" + pathHTML + secure_filename(f.filename))
        os.remove("./tmp/"+pathPDF+secure_filename(f.filename))




        cmd_line = "pwd"
        pwd = subprocess.run(cmd_line, capture_output=True)
        pwd = pwd.stdout.decode("utf-8").replace('\n', '')

        cmd_line = "docker run --rm -v " + pwd +"/media/"+ pathHTML+ ":/pdf bwits/pdf2htmlex-alpine pdf2htmlEX "+secure_filename(f.filename)
        print(cmd_line)
        html = os.system(cmd_line)
        print('docker',html)
        os.remove(pwd +"/media/"+ pathHTML + secure_filename(f.filename))

        htmlcouleur = processColoration(join(pwd+"/media/"+ pathHTML, secure_filename(f.filename).replace('pdf','html')),join(pwd+"/media/"+ pathHTMLCouleur, secure_filename(f.filename).replace('pdf','html')))







        m = Dossier(url="./media/"+pathPDF+secure_filename(f.filename))
        if htmlcouleur != 0:
            m.urlhtmlcouleur = htmlcouleur
        m.urlhtml = "./media/"+ pathHTML + secure_filename(f.filename).replace('pdf','html')
        m.fullhash=hash
        m.numero=f.filename.split('-')[1]
        m.nom=f.filename.split('-')[2].split('.')[0]
        m.type=f.content_type
        m.id_owner = current_user.id
        m.id_groupe = g
        m.reservation=0
        db.session.add(m)
        db.session.commit()

        return jsonify({'path':"/media/"+str(m.id),'type':m.type})


#------------------------ GROUPE

@app.route('/groupes/registration' ,methods=['POST'])
@token_required
def registrationGroupe(current_user):
    if current_user.rank!=0:
        return jsonify([])

    if request.json.get('name') == None:
        return jsonify([])
    groupe = Groupe(nom=request.json.get('name'))

    db.session.add(groupe)
    db.session.commit()

    detail1 = ConfigurationDetail(pourcentageRelectureAcceptation=0,pourcentageRelectureRefus=0,lecture=0, coloration=1)
    detail2 = ConfigurationDetail(pourcentageRelectureAcceptation=0,pourcentageRelectureRefus=0,lecture=0, coloration=1)
    detail3 = ConfigurationDetail(pourcentageRelectureAcceptation=0,pourcentageRelectureRefus=0,lecture=0, coloration=1)
    db.session.add(detail1)
    db.session.add(detail2)
    db.session.add(detail3)
    db.session.commit()

    defaut = Configuration.query.filter_by(id_groupe=-1).first()
    configuration = Configuration(id_groupe=groupe.id)
    if defaut is not None:
        configuration.motsPositif = defaut.motsPositif
        configuration.motsNegatif = defaut.motsNegatif

    configuration.phase1= detail1.id
    configuration.phase2 = detail2.id
    configuration.phase3 = detail3.id

    db.session.add(configuration)
    db.session.commit()
    print(configuration.serialize())
    return jsonify(groupe.serialize())


@app.route('/groupes/delete' ,methods=['POST'])
@token_required
def delGroupe(current_user):
    print(request.json.get('id'))
    if current_user.rank!=0:
        return jsonify([])

    if request.json.get('id') == None:
        return jsonify([])

    groupe = Groupe.query.filter_by(id=request.json.get('id')).first()
    if groupe is not None:
        configurations = Configuration.query.filter_by(id_groupe=groupe.id).all()
        for c in configurations:
            d1=ConfigurationDetail.query.filter_by(id=c.phase1).delete()
            d2 = ConfigurationDetail.query.filter_by(id=c.phase2).delete()
            d3 = ConfigurationDetail.query.filter_by(id=c.phase3).delete()
            db.session.delete(c)
        permission = Permission.query.filter_by(id_groupe=groupe.id).delete()
        db.session.commit()
    return jsonify([])


@app.route("/groupes")
@token_required
def getGroupe(current_user):



    groups = Groupe.query.all()
    data = []

    for g in groups:

        gs = g.serialize()
        #print("getGroupe",gs)
        conf = Configuration.query.filter_by(id_groupe=g.id).first()
        #print("conf groupe",conf.phase1, conf.phase2, conf.phase3)
        detail1=ConfigurationDetail.query.filter_by(id=conf.phase1).first()
        detail2 = ConfigurationDetail.query.filter_by(id=conf.phase2).first()
        detail3 = ConfigurationDetail.query.filter_by(id=conf.phase3).first()

        gs["configuration"]=conf.serialize()
        gs["configuration"]["phase1"]=detail1.serialize()
        gs["configuration"]["phase2"] = detail2.serialize()
        gs["configuration"]["phase3"] = detail3.serialize()

        dossier = Dossier.query.filter_by(id_groupe=g.id).all()
        gs['nbDossierPhase1']=len(dossier)
        sql="""SELECT dossier.id,dossier.id_groupe,count(dossier.id),resultat
        FROM dossier,resultat 
        WHERE dossier.id=resultat.id_dossier 
        AND resultat=-1
        AND dossier.id_groupe="""+str(g.id)+"""
        GROUP BY dossier.id,dossier.id_groupe,resultat
        HAVING count(dossier.id)=1"""
        res = db.session.execute(sql)
        sql2= """SELECT dossier.id,dossier.id_groupe,count(dossier.id),resultat
                FROM dossier,resultat 
                WHERE dossier.id=resultat.id_dossier 
                AND resultat=1
                AND dossier.id_groupe="""+str(g.id)+"""
                GROUP BY dossier.id,dossier.id_groupe,resultat
                HAVING count(dossier.id)=1"""
        res2 = db.session.execute(sql2)





        gs['nbDossierPhase2'] = len(list(res))*gs["configuration"]["phase2"]["pourcentageRelectureRefus"]/100 + len(list(res2))*gs["configuration"]["phase2"]["pourcentageRelectureAcceptation"]/100
        gs['nbDossierPhase3']=0
        avancement= []
        for d in dossier:
            res = Resultat.query.filter_by(id_dossier=d.id).all()
            if res is not None:
                avancement.append(len(res))
        gs["avancement"] = {}
        gs["avancement"]["phase1"] = avancement.count(1)
        gs["avancement"]["phase2"] = avancement.count(2)
        gs["avancement"]["phase3"] = avancement.count(3)

        lecteur = Permission.query.filter_by(id_groupe=g.id).all()
        gs["nbLecteur"]=len(lecteur)
        data.append(gs)
    return jsonify(data)


#------------------------ Configuration
@app.route('/configuration/update/groupe/<int:id>',methods=['POST'])
@token_required
def updateConfigurationGroup(current_user,id):
    if current_user.rank!=0:
        return jsonify([])

    configuration = Configuration.query.filter_by(id_groupe=id).first()
    if configuration is not None:
        detail = None
        if request.json.get("phase") == "phase1":
            detail = ConfigurationDetail.query.filter_by(id=configuration.phase1).first()
        if request.json.get("phase") == "phase2":
            detail = ConfigurationDetail.query.filter_by(id=configuration.phase2).first()
        if request.json.get("phase") == "phase3":
            detail = ConfigurationDetail.query.filter_by(id=configuration.phase3).first()

        if detail is not None:
            if request.json.get("type")=="lecture":
                detail.lecture=request.json.get("value")
            if request.json.get("type")=="coloration":
                detail.coloration=request.json.get("value")
            if request.json.get("type")=="pourcentageRelectureRefus":
                detail.pourcentageRelectureRefus=request.json.get("value")
            if request.json.get("type")=="pourcentageRelectureAcceptation":
                detail.pourcentageRelectureAcceptation=request.json.get("value")

    db.session.commit()

    return jsonify([])



@app.route('/configuration/update',methods=['POST'])
@token_required
def updateConfiguration(current_user):


    if current_user.rank!=0:
        return jsonify([])

    configuration = Configuration.query.all()
    data = []
    for c in configuration:
        data.append(c.serialize())
        if request.json.get("type") == "feedbackAcceptation":
            c.feedbackAcceptation=request.json.get("value")
        if request.json.get("type") == "feedbackRefus":
            c.feedbackRefus=request.json.get("value")
        if request.json.get("type") == "feedbackRefus":
            c.motsPositif=request.json.get("value")
        if request.json.get("type") == "motsPositif":
            c.motsPositif=request.json.get("value")
        if request.json.get("type") == "motsNegatif":
            c.motsNegatif=request.json.get("value")

    db.session.commit()

    return jsonify(data)



@app.route('/configuration/groupe',methods=['POST'])
@token_required
def getConfigurationGroupe(current_user):

    #print(request.json.get("id"))
    if request.json.get("id") ==None:
        configuration = Configuration.query.first()
    else:
        configuration = Configuration.query.filter_by(id_groupe=request.json.get("id")).first()
    if configuration is not None:
        return jsonify(configuration.serialize())

    return jsonify([])

#------------------------ DOSSIER



@app.route('/myDossier', methods=['GET'])
@token_required
def myDossier(current_user):
    dossier = Dossier.query.filter_by(reservation=current_user.id).first()

    if dossier is not None:
        return jsonify(dossier.serialize())
    return jsonify({})

@app.route('/dossiers/coloration', methods=['GET'])
@token_required
def coloration_dossier(current_user):

    if current_user.rank != 0:
        return make_response('Could not verify', 405, {'WWW-Authenticate': 'Basic realm="Admin required!"'})


    dossier=Dossier.query.all()
    for d in dossier:
        print(d.urlhtmlcouleur)
        if d.urlhtmlcouleur is not None:
            os.remove(d.urlhtmlcouleur)
            processColoration(d.urlhtml,d.urlhtmlcouleur)



    return jsonify({})

@app.route('/dossier/trash/<int:id>', methods=['DELETE'])
@token_required
def del_dossier(current_user,id):
    #print("del",current_user)
    if current_user.rank != 0:
        return make_response('Could not verify', 405, {'WWW-Authenticate': 'Basic realm="Admin required!"'})


    dossier=Dossier.query.filter_by(id=id).delete()

    #print(dossier)
    db.session.commit()

    return jsonify({"id":id})



@app.route('/resultats/delete', methods=['POST'])
@token_required
def resultats(current_user):
    #print("del",current_user,request.json)
    #if current_user.rank != 0:
    #    return make_response('Could not verify', 405, {'WWW-Authenticate': 'Basic realm="Admin required!"'})

    if request.json.get("dossier") is not None:
        if request.json.get('user',None) is None:
            resultats = Resultat.query.filter_by(id_dossier=request.json.get("dossier")["id"]).all()
        else:
            resultats = Resultat.query.filter_by(id_user=request.json.get('user'),id_dossier=request.json.get("dossier")["id"]).all()
        for r in resultats:
            db.session.delete(r)

    db.session.commit()
    return jsonify([])

@app.route('/resultats/registration', methods=['POST'])
@token_required
def resultats_registration(current_user):
    print("res",request.json.get("reponse"))


    dossier=Dossier.query.filter_by(reservation=current_user.id).first()
    if dossier is not None:
        resultat = Resultat(id_user=current_user.id, id_dossier=request.json.get("dossier")["id"],
                            resultat=request.json.get("reponse")["resultat"])
        if "motif" in request.json.get("reponse").keys():
            resultat.motif = request.json.get("reponse")['motif']
        db.session.add(resultat)
        dossier.reservation=0
        db.session.commit()

    return getdossier2(current_user,1)



@app.route('/dossiers')
@token_required
def getDossiers(current_user):
    dossiers = Dossier.query.all()


    data = []
    for d in dossiers:
        ds = d.serialize()
        groupe = Groupe.query.filter_by(id=d.id_groupe).first()
        if groupe is not None:
            ds['nomGroupe'] = groupe.serialize()
            ds['groupe'] = ds['nomGroupe']["nom"]
        else:
            groupe = Groupe()
            groupe.id=-1
            groupe.nom="[supprime]"
            ds['nomGroupe'] = groupe.serialize()
            ds['groupe'] =  ds['nomGroupe']["nom"]


        resultat = Resultat.query.filter_by(id_dossier=d.id).all()
        for i in range(0,3):
            if len(resultat) > i:
                rs = resultat[i].serialize()
                relecteur = User.query.filter_by(id=rs['id_user']).first()
                if relecteur is not None:
                    rs["relecteur"]=User.query.filter_by(id=rs['id_user']).first().serialize()
                else : 
                    rs["relecteur"]={"firstname":"supprimé","lastname":"supprimé"}
                ds['resultat'+str(i+1)]=rs
            else:
                ds['resultat' + str(i+1)] = None

        data.append(ds)

    return jsonify(data)


@app.route('/dossiers/user')
@token_required
def getDossiersUser(current_user):
    data = []
    #print('getDossiersUser ',current_user.id)

    resultat = Resultat.query.filter_by(id_user=current_user.id).all()
    for r in resultat:
        dossier = Dossier.query.filter_by(id=r.id_dossier).first()
        if dossier is not None:
            ds=dossier.serialize()
            ds["resultat"]=r.serialize()
            data.append(ds)
            #print(data)

    return jsonify(data)



@app.route('/configuration')
def configuration():
    user = User.query.filter_by(rank=0).all()
    if user is not None and len(user)!=0:
        data=[]
        for u in user:
            data.append({"name":u.lastname,"mail":u.mail})
        return jsonify(data)
    u = User(mail="baudouin.dafflon@univ-lyon1.fr")
    u.password = generate_password_hash("azerty")
    u.rank = 0
    db.session.add(u)

    u2 = User(mail="etu@gmp.fr")
    u2.password = generate_password_hash("azerty")
    u2.rank = 0
    db.session.add(u2)
    db.session.commit()
    return jsonify({"message":"ok"})
 
if __name__ == '__main__':
    #powershell  : $env:FLASK_APP = api.py
    #CMD set FLASK_APP=api.py
    #error : flask db revision --rev-id c555609ffc5c
    app.run(host="0.0.0.0", debug=True,port=8127)
