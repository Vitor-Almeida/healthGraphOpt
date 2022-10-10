import pickle
from data_sus import graph_data
import os

def load_data(initialTime,durationTime):

    if not os.path.exists('./data/bin/patTypeList.pkl'):

        data = graph_data(initialTime,durationTime)
        Demandpat = data.Demandpat
        qtdCovidReal = data.qtdCovidReal
        CONCapacityrh  = data.CONCapacityrh
        CONCapacityrhCancer = data.CONCapacityrhCancer
        InitPatientsph  = data.InitPatientsph
        releasePatientspht  = data.releasePatientspht
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
        with open('./data/bin/Demandpat.pkl', 'rb') as f:
            Demandpat=pickle.load(f)
            f.close()
        with open('./data/bin/CONCapacityrh.pkl', 'rb') as f:
            CONCapacityrh=pickle.load(f)
            f.close()
        with open('./data/bin/InitPatientsph.pkl', 'rb') as f:
            InitPatientsph=pickle.load(f)
            f.close()
        with open('./data/bin/releasePatientspht.pkl', 'rb') as f:
            releasePatientspht=pickle.load(f)
            f.close()
        with open('./data/bin/LOSp.pkl', 'rb') as f:
            LOSp=pickle.load(f)
            f.close()
        with open('./data/bin/Distanceah.pkl', 'rb') as f:
            Distanceah=pickle.load(f)
            f.close()
        with open('./data/bin/CONCapacityrhCancer.pkl', 'rb') as f:
            CONCapacityrhCancer = pickle.load(f)
            f.close()
        with open('./data/bin/qtdCovidReal.pkl', 'rb') as f:
            qtdCovidReal = pickle.load(f)
            f.close()

    return patTypeList,areaIdList,hosIdList,equipTypeList,tList,Demandpat,CONCapacityrh,InitPatientsph,releasePatientspht,LOSp,Distanceah,CONCapacityrhCancer,qtdCovidReal