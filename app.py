import json
from flask import Flask, render_template, request
import pymongo
from bs4 import  BeautifulSoup
import requests
import ssl
import pandas as pd
from joblib import load
import numpy as np

app = Flask(__name__)

client = pymongo.MongoClient("your mongodb connection string")
db = client['Resultanalyze']


@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/generate/',methods=['POST'])
def gene():
    sem=request.form['sem']
    branch=request.form['branch']
    batch=request.form['batch']
    sec=request.form['sec']
    endroll=request.form['endroll']
    missnum=request.form['missnum']

    table = db[branch]
    def generate():
        no_res=0
        url = "https://doeresults.gitam.edu/onlineresults/pages/newgrdcrdinput1.aspx"
        s = requests.Session()
        response = s.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        login_data = {}
        states = ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION', '__EVENTTARGET',
                  '__EVENTARGUMENT']
        for aspnet in states:
            result = soup.find('input', {'name': aspnet})
            if not (result is None):
                login_data.update({aspnet: result['value']})

        sem1 = sem
        size = int(endroll[-2:])
        roll1=int(endroll[:-2]+"01")
        for i in range(size):
            login_data.update(
                {
                    "cbosem": sem1,
                    "txtreg": roll1,
                    "Button1": "Get Result"})

            open = s.post(url, data=login_data)
            so = BeautifulSoup(open.text, "html.parser")
            if so.title.text.strip() != "GITAM Examination Results":
                name = so.find('span', {"id": "lblname"}).text  # finding student's name
                regdno = so.find('span', {"id": "lblregdno"}).text  # finding student's registration number
                res = so.find('table', {
                    "id": "GridView1"})  # grades will be stored in the form a table- finding the table for data
                indiresult = {}  # dictionary
                indiresult['Name'] = name
                indiresult['Regdno'] = int(regdno)
                indiresult['Branch'] = branch
                indiresult['Sem'] = int(sem1)
                indiresult['Batch'] = batch
                indiresult['Section']=sec
                h = res.find_all('td')  # student complete grades of subjects finding
                result = {}  # dictionary
                course_result = []  # list
                i = 0
                while (i < len(h)):
                    result['Course_code'] = h[i].text
                    result['Course_name'] = h[i + 1].text
                    result['Course_grade'] = h[i + 3].text
                    course_result.append(result.copy())
                    i += 4
                indiresult['Result'] = course_result  # inserting total course result(dictionary) into result key
                indiresult['GPA'] = float(so.find('span', {"id": "lblgpa"}).text)  # finding gpa
                indiresult['CGPA'] = float(so.find('span', {"id": "lblcgpa"}).text)  # finding cgpa
                table.insert_one(indiresult)

            else:
                no_res+=1
            roll1 += 1

        totalstrength=int(size)-int(missnum)
        nores={'Noresult':no_res-int(missnum),'Branch':branch,'Sem':int(sem1),'Section':sec,'Batch':batch,'result':'noresult'}
        table.insert_one(nores)
        totalstd={'totalstd':totalstrength,'Branch':branch,'Sem':int(sem1),'Section':sec,'Batch':batch,'classsize':'totalstrength'}
        table.insert_one(totalstd)

    response=table.find({'Sem':int(sem),'Batch':batch,'Branch':branch,'Section':sec}).count()
    if(response==0):
        generate()
        return "Process Completed. Please Check Total Semester View "
    else:
        return "Already Data Present For Given Input. Please Check Total Semester View. "



@app.route('/getdata/',methods=['POST'])
def getdata():
    sem= request.form['sem']
    batch= request.form['batch']
    branch=request.form['branch']
    sec=request.form['section']
    mycol = db[branch]
    isdata=mycol.find({'Sem':int(sem),'Batch':batch,'Branch':branch,'Section':sec}).count()
    k=mycol.find({'Sem':int(sem),'Batch':batch,'Branch':branch,'Section':sec})
    li=list()
    d = {}
    subjects = list()
    stdpass = list()
    passperc = list()
    if isdata >0:
        for i in k:
            li.append(i)
        li.pop()
        li.pop()
        i=0
        for r in li[1]['Result']:
            subjects.append(r['Course_code']+":"+r['Course_name'])
            d[subjects[i]]=[]
            i+=1
        noresult = mycol.find({'result': 'noresult','Sem':int(sem),'Batch':batch,'Branch':branch,'Section':sec})
        noresult = list(noresult)
        totalstrength=mycol.find({'classsize':'totalstrength','Sem':int(sem),'Batch':batch,'Branch':branch,'Section':sec})
        totalstrength=list(totalstrength)

        for i in subjects:
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:],'Course_grade':'O'}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'A+',}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'A'}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'B+'}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'B'}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'C'}},'Section':sec}).count())
            d[i].append(mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'P'}},'Section':sec}).count())
            f=mycol.find({'Result': {'$elemMatch': {'Course_name': i[i.find(":")+1:], 'Course_grade': 'F'}},'Section':sec}).count()
            d[i].append(f)
            stdpass.append(totalstrength[0]['totalstd']-(f+noresult[0]['Noresult']))
            pasper=((totalstrength[0]['totalstd'] - (f + noresult[0]['Noresult'])) / totalstrength[0]['totalstd']) * 100
            pasper="{:.2f}".format(pasper)
            passperc.append(pasper)
            global barchartd
            global barchartsub
            global barchartstd
            global barchartpassperc
            barchartd=d.copy()
            barchartsub=subjects.copy()
            barchartstd=stdpass.copy()
            barchartpassperc=passperc.copy()
            
        return render_template('totalviewdisplay.html',li=li,subj=subjects,len=len(li[1]['Result']),gradecount=d,nores=noresult[0]['Noresult'],stdpass=stdpass,totalstrength=totalstrength[0]['totalstd'],passperc=passperc,br=branch)
    else:
        return "Data Not Found. Please Generate.."

@app.route('/totalview/charts/',methods=['POST'])
def charts():
    chartbranch=request.form['branch']
    mycol = db[chartbranch]
    noresult = mycol.find({'result': 'noresult'})
    noresult = list(noresult)
    totalstrength = mycol.find({'classsize': 'totalstrength'})
    totalstrength = list(totalstrength)
    return render_template('barchart.html',gradecount=barchartd,subj=barchartsub,nores=noresult[0]['Noresult'],stdpass=barchartstd,totalstrength=totalstrength[0]['totalstd'],passperc=barchartpassperc)


@app.route('/totalview/')
def totalview():
    return render_template('totalview.html')

@app.route('/individualview/')
def indiview():
    return render_template('individualview.html')

@app.route('/getsubject',methods=['POST'])
def getsub():
    batch = request.form['batch']
    branch = request.form['branch']
    sec = request.form['section']
    sem=int(request.form['sem'])
    co = db[branch]
    if sec!='':
        sub = co.distinct('Result',{'Batch': batch, 'Branch': branch, 'Section': sec,'Sem':sem})
        if sub:
            sub = list(sub)
            subli = list()
            for i in sub:
                subli.append(i['Course_name'])
            return json.dumps(list(set(subli)))
        else:
            return "Data Not Found.Please Generate.."
    else:
        sub = co.distinct('Result', {'Batch': batch, 'Branch': branch, 'Sem': sem})
        if sub:
            sub = list(sub)
            subli = list()
            for i in sub:
                subli.append(i['Course_name'])
            return json.dumps(list(set(subli)))
        else:
            return "Data Not Found.Please Generate.."

@app.route('/indiview',methods=['POST'])
def getindivew():
    batch = request.form['batch']
    branch = request.form['branch']
    sec = request.form['section']
    sec2 = request.form['section2']
    sem = int(request.form['sem'])
    sub=request.form['sub']
    tab=db[branch]
    def getin(section):
        if len(section)==1:
            sname=[sub+'-'+section[0]]
            data1={sname[0]:[]}
        else:
            sname=[sub+'-'+section[0],sub+'-'+section[1]]
            data1={sname[0]:[],sname[1]:[]}
        cg = ['O', 'A+', 'A', 'B+', 'B', 'C', 'P']
        studentp=[]
        passpercent=[]
        nore=[]
        ttstd=[]
        h=0
        for o in section:
            for c in cg:
                data1[sub+'-'+o].append(tab.find({'Result': {'$elemMatch': {'Course_name': sub, 'Course_grade': c}}, 'Section': o}).count())
            failures = tab.find({'Result': {'$elemMatch': {'Course_name': sub, 'Course_grade': 'F'}}, 'Section': o}).count()
            data1[sub+'-'+o].append(failures)
            ttstd.append((tab.find({'classsize': 'totalstrength', 'Sem': sem, 'Batch': batch, 'Branch': branch, 'Section': o}))[0]['totalstd'])
            nore.append((tab.find({'result': 'noresult', 'Sem': int(sem), 'Batch': batch, 'Branch': branch, 'Section': o}))[0]['Noresult'])
            studentp.append(ttstd[h]- (failures + nore[h]))
            passpercent.append("{:.2f}".format((((ttstd[h] - (failures + nore[h])) / ttstd[h]) * 100)))
            h+=1
        return [sname,data1,nore,studentp,ttstd[0], passpercent]
    if sec2!='0':
        indi = tab.find({'Batch': batch, 'Sem': int(sem), 'Branch': branch, 'Section': { '$in': [ sec,sec2 ] },'result':{'$nin':['noresult']},'classsize':{'$nin':['totalstrength']}})
        indi = list(indi)
        indili1=[]
        indili2=[]
        indires1=dict()
        indires2=dict()
        flag=0
        for j in indi:
            if j['Section']==sec:
                flag=1
                for h in j['Result']:
                    if h['Course_name']==sub:
                        indires1['rollnum']=j['Regdno']
                        indires1['grade']=h['Course_grade']
            else:
                flag=0
                for p in j['Result']:
                    if p['Course_name']==sub:
                        indires2['rollnum']=j['Regdno']
                        indires2['grade']=p['Course_grade']
            if flag==1:
                indili1.append(indires1.copy())
            else:
                indili2.append(indires2.copy())
        op = [sec,sec2]
        k = getin(op)
        return render_template('indiview.html',subjectn=sub,indili1=indili1,indili2=indili2,subname=k[0],gradc=k[1],nore=k[2],studentp=k[3],ttstd=k[4],passpercent=k[5])
    else:
        indi=tab.find({'Batch':batch,'Sem':int(sem),'Branch':branch,'Section':sec})
        indi=list(indi)
        indi.pop()
        indi.pop()
        indires=dict()
        indili=[]
        for j in indi:
            for h in j['Result']:
                if h['Course_name']==sub:
                    indires['rollnum']=j['Regdno']
                    indires['grade']=h['Course_grade']
            indili.append(indires.copy())
        op=[sec]
        k=getin(op)
        return render_template('indiview.html', indili=indili, subname=k[0],gradc=k[1],nore=k[2],studentp=k[3],ttstd=k[4],passpercent=k[5])


@app.route('/studentperformance/')
def perforview():
    return render_template('studentperformance.html')

@app.route('/getstd',methods=['POST'])
def getstd():
    batch = request.form['batch']
    branch = request.form['branch']
    sec = request.form['section']
    col = db[branch]
    std=col.distinct('Regdno',{'Batch':batch,'Branch':branch,'Section':sec})
    if std:
        std=list(std)
        stdli=list()
        for i in std:
            stdli.append(i)
        return json.dumps(stdli)
    else:
        return "Data Not Found.Please Generate.."

@app.route('/performance',methods=['POST'])
def stdperform():
    batch = request.form['batch']
    branch = request.form['branch']
    sec = request.form['section']
    std=request.form['std']
    col=db[branch]
    stdper = col.find({'Batch': batch, 'Branch': branch, 'Section': sec,'Regdno':int(std)}).count()
    if stdper:
        sper=col.find({'Batch': batch, 'Branch': branch, 'Section': sec,'Regdno':int(std)})
        studentperformance=dict()
        for i in sper:
            studentperformance[i['Sem']]=i['CGPA']
        for i in range(1,9):
            if i in studentperformance:
                continue
            else:
                studentperformance[i]=0
        return render_template("performance.html",sperf=studentperformance,std=std,l=0)
    else:
        return "Data not found."

@app.route('/graphicalview/')
def graphicalview():
    return render_template('graphicalview.html')

@app.route('/getgraph',methods=['POST'])
def graphdata():
    sem1 = request.form['sem']
    batch1 = request.form['batch']
    branch1 = request.form['branch']
    sec1 = request.form['section']
    mycol1 = db[branch1]
    isdata1 = mycol1.find({'Sem': int(sem1), 'Batch': batch1, 'Branch': branch1, 'Section': sec1}).count()
    k1 = mycol1.find({'Sem': int(sem1), 'Batch': batch1, 'Branch': branch1, 'Section': sec1})
    li1 = list()
    d1 = {}
    subjects1 = list()
    stdpass1 = list()
    passperc1 = list()
    if isdata1 > 0:
        for i in k1:
            li1.append(i)

        li1.pop()
        li1.pop()
        i = 0
        for r in li1[1]['Result']:
            subjects1.append(r['Course_code'] + ":" + r['Course_name'])
            d1[subjects1[i]] = []
            i += 1
        noresult1 = mycol1.find({'result': 'noresult','Sem':int(sem1),'Batch':batch1,'Branch':branch1,'Section':sec1})
        noresult1 = list(noresult1)
        totalstrength1 = mycol1.find({'classsize': 'totalstrength','Sem':int(sem1),'Batch':batch1,'Branch':branch1,'Section':sec1})
        totalstrength1 = list(totalstrength1)

        for i in subjects1:
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'O'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'A+'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'A'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'B+'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'B'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'C'}},'Section':sec1}).count())
            d1[i].append(mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'P'}},'Section':sec1}).count())
            f = mycol1.find(
                {'Result': {'$elemMatch': {'Course_name': i[i.find(":") + 1:], 'Course_grade': 'F'}},'Section':sec1}).count()
            d1[i].append(f)
            stdpass1.append(totalstrength1[0]['totalstd'] - (f + noresult1[0]['Noresult']))
            pasper1 = ((totalstrength1[0]['totalstd'] - (f + noresult1[0]['Noresult'])) / totalstrength1[0]['totalstd']) * 100
            pasper1 = "{:.2f}".format(pasper1)
            passperc1.append(pasper1)

        return render_template('barchart.html', gradecount=d1, subj=subjects1, nores=noresult1[0]['Noresult'],stdpass=stdpass1, totalstrength=totalstrength1[0]['totalstd'],passperc=passperc1)
    else:
        return "Data Not Found. Please Generate.."

##Prediction ##
@app.route('/gpredict',methods=['POST'])
def gradepredict():
    semp = int(request.form['semp'])
    subjp=request.form['subjp']
    imarks=int(request.form['imarks'])
    data = pd.read_csv("predict/sem"+str(semp)+'.csv')
    x = data.iloc[:, 0:1].values
    ct = load("predict/Transform_"+str(semp))
    x = ct.fit_transform(x)
    x = x[:,1:]
    d={}
    for i in range(data.shape[0]):
        d[data.iloc[i,0]] = x[i,:]
    model = load("predict/Models/sem_"+str(semp))
    d[subjp] = np.append(d[subjp],[imarks])
    k=round(model.predict([d[subjp]])[0])
    grad={10:'O',9:'A+',8:'A',7:'B+',6:'B',5:'C',4:'P',3:'F',2:'F',1:'F',0:'F'}
    return grad[k]



if __name__ == '__main__':
    app.run(threaded=True)
