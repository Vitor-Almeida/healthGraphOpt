import pickle
from dataloader.data_sus import graph_data
import os

def load_data(initialTime,durationTime):

    if not os.path.exists('./data/bin/patTypeList.pkl'):

        data = graph_data(initialTime,durationTime)
        DemandCancerpat = data.DemandCancerpat
        qtdCovidReal = data.qtdCovidReal
        CONCapacityrhCancer = data.CONCapacityrhCancer
        InitPatientsph  = data.InitPatientsphCancer
        releasePatientspht  = data.releasePatientsphtCancer
        qtdProf = data.qtdProf
        qtdPuraCovidReal = data.qtdPuraCovidReal
        qtdTT = data.qtdTT
        LOSp = data.LOSp
        Distanceah = data.Distanceah

        #############################
        # Step 1: Define index sets #
        patTypeList = data.patTypeList
        equipTypeList = data.equipIdList
        areaIdList = data.areaIdList
        hosIdList = data.hosIdList
        tList = data.tList
        #                           #
        #############################

    else:

        with open('./data/bin/patTypeList.pkl', 'rb') as f:
            patTypeList=pickle.load(f)
            f.close()
        with open('./data/bin/areaIdList.pkl', 'rb') as f:
            areaIdList=pickle.load(f)
            f.close()
        with open('./data/bin/hosIdList.pkl', 'rb') as f:
            hosIdList=pickle.load(f)
            f.close()
        with open('./data/bin/equipIdList.pkl', 'rb') as f:
            equipTypeList=pickle.load(f)
            f.close()
        with open('./data/bin/tList.pkl', 'rb') as f:
            tList=pickle.load(f)
            f.close()
        with open('./data/bin/DemandCancerpat.pkl', 'rb') as f:
            DemandCancerpat=pickle.load(f)
            f.close()
        with open('./data/bin/CONCapacityrhCancer.pkl', 'rb') as f:
            CONCapacityrhCancer=pickle.load(f)
            f.close()
        with open('./data/bin/InitPatientsphCancer.pkl', 'rb') as f:
            InitPatientsph=pickle.load(f)
            f.close()
        with open('./data/bin/releasePatientsphtCancer.pkl', 'rb') as f:
            releasePatientspht=pickle.load(f)
            f.close()
        with open('./data/bin/LOSp.pkl', 'rb') as f:
            LOSp=pickle.load(f)
            f.close()
        with open('./data/bin/Distanceah.pkl', 'rb') as f:
            Distanceah=pickle.load(f)
            f.close()
        with open('./data/bin/qtdCovidReal.pkl', 'rb') as f:
            qtdCovidReal = pickle.load(f)
            f.close()
        with open('./data/bin/qtdProf.pkl', 'rb') as f:
            qtdProf = pickle.load(f)
            f.close()
        with open('./data/bin/qtdPuraCovidReal.pkl', 'rb') as f:
            qtdPuraCovidReal = pickle.load(f)
            f.close()
        with open('./data/bin/qtdTT.pkl', 'rb') as f:
            qtdTT = pickle.load(f)
            f.close()

    dataDic = {'patTypeList':patTypeList,'areaIdList':areaIdList,'hosIdList':hosIdList,'equipTypeList':equipTypeList,'tList':tList,'DemandCancerpat':DemandCancerpat,
                'CONCapacityrhCancer':CONCapacityrhCancer,'InitPatientsph':InitPatientsph,'releasePatientspht':releasePatientspht,
                'LOSp':LOSp,'Distanceah':Distanceah,'qtdCovidReal':qtdCovidReal,'qtdProf':qtdProf,'qtdPuraCovidReal':qtdPuraCovidReal,
                'qtdTT':qtdTT}

    return dataDic
    #return patTypeList,areaIdList,hosIdList,equipTypeList,tList,DemandCancerpat,CONCapacityrhCancer,InitPatientsph,releasePatientspht,LOSp,Distanceah,qtdCovidReal,qtdProf,qtdPuraCovidReal,qtdTT